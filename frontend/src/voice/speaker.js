// Speak text: Gemini TTS first, browser speechSynthesis as the fallback
// (slow network, rate limit, or VITE_USE_GEMINI_TTS=false for the demo).
import { post } from "./api";

const USE_GEMINI = import.meta.env.VITE_USE_GEMINI_TTS !== "false";
const TTS_TIMEOUT_MS = 7000;

export const BCP47 = { en: "en-US", es: "es-US", zh: "zh-CN", vi: "vi-VN", tl: "fil-PH", ar: "ar-SA" };

let currentAudio = null;
let pendingResolve = null;

export function stopSpeaking() {
  if (currentAudio) { currentAudio.pause(); currentAudio = null; }
  window.speechSynthesis?.cancel();
  if (pendingResolve) { pendingResolve(); pendingResolve = null; }
}

export async function speak(text, lang) {
  if (!text) return;
  stopSpeaking();
  if (USE_GEMINI) {
    try {
      const ctrl = new AbortController();
      const t = setTimeout(() => ctrl.abort(), TTS_TIMEOUT_MS);
      const res = await post("/voice/tts", { text, language: lang }, { signal: ctrl.signal });
      clearTimeout(t);
      if (res.audio_b64) return await playAudio(`data:${res.mime_type};base64,${res.audio_b64}`);
    } catch {
      /* fall through to the browser voice */
    }
  }
  return browserSpeak(text, lang);
}

function playAudio(src) {
  return new Promise((resolve) => {
    const audio = new Audio(src);
    currentAudio = audio;
    pendingResolve = resolve;
    const done = () => { if (currentAudio === audio) currentAudio = null; pendingResolve = null; resolve(); };
    audio.onended = done;
    audio.onerror = done;
    audio.play().catch(done);
  });
}

function pickVoice(lang) {
  const voices = window.speechSynthesis.getVoices();
  const full = BCP47[lang] || lang;
  return voices.find((v) => v.lang === full) || voices.find((v) => v.lang.startsWith(lang));
}

function browserSpeak(text, lang) {
  return new Promise((resolve) => {
    if (!window.speechSynthesis) return resolve();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = BCP47[lang] || lang;
    const voice = pickVoice(lang);
    if (voice) u.voice = voice;
    u.rate = 0.92; // a little slower for clarity
    pendingResolve = resolve;
    // Chrome sometimes never fires onend — safety timeout based on length.
    const safety = setTimeout(() => finish(), 4000 + text.length * 90);
    function finish() { clearTimeout(safety); pendingResolve = null; resolve(); }
    u.onend = finish;
    u.onerror = finish;
    window.speechSynthesis.speak(u);
  });
}

// Voices load async in Chrome; touch the list early.
if (typeof window !== "undefined" && window.speechSynthesis) {
  window.speechSynthesis.getVoices();
  window.speechSynthesis.onvoiceschanged = () => window.speechSynthesis.getVoices();
}
