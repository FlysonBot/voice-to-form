import { useCallback, useEffect, useState } from 'react';
import { pickVoice } from '../i18n/speechLang';

const supported = typeof window !== 'undefined' && 'speechSynthesis' in window;

export interface SpeakHandlers {
  /** Fired per spoken word when the voice supports it (charIndex, charLength) */
  onBoundary?: (charIndex: number, charLength: number) => void;
  /** Fired once when speech finishes, errors, or is cancelled */
  onEnd?: () => void;
}

/** Text-to-speech through the browser's built-in voices. */
export function useSpeaker() {
  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>(() => (supported ? speechSynthesis.getVoices() : []));

  // Chrome loads its voice list asynchronously
  useEffect(() => {
    if (!supported) return;
    const load = () => setVoices(speechSynthesis.getVoices());
    load();
    speechSynthesis.addEventListener('voiceschanged', load);
    return () => speechSynthesis.removeEventListener('voiceschanged', load);
  }, []);

  /** Returns false when nothing will be spoken (no support, unknown language, or no voice). */
  const speak = useCallback((text: string, bcp47: string | undefined, handlers: SpeakHandlers = {}) => {
    if (!supported || !bcp47 || !text.trim()) return false;
    const list = speechSynthesis.getVoices(); // fresh read, in case state hasn't caught up yet
    const voice = pickVoice(list, bcp47);
    if (list.length > 0 && !voice) return false;

    speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    if (voice) u.voice = voice;
    u.lang = voice?.lang ?? bcp47;
    u.rate = 0.95;

    let ended = false;
    // Chrome sometimes never fires "end"; force it after a generous estimate
    const safety = window.setTimeout(() => finish(), 4000 + text.length * 120);
    function finish() {
      if (ended) return;
      ended = true;
      window.clearTimeout(safety);
      handlers.onEnd?.();
    }

    u.onboundary = (e) => {
      if (e.name === 'word' || e.name === undefined) handlers.onBoundary?.(e.charIndex, e.charLength ?? 0);
    };
    u.onend = finish;
    u.onerror = finish; // includes "interrupted" when cancelled

    // Keep a reference so the utterance isn't garbage-collected mid-speech (Chrome bug)
    (window as unknown as { __utterance?: SpeechSynthesisUtterance }).__utterance = u;
    speechSynthesis.speak(u);
    return true;
  }, []);

  const cancel = useCallback(() => {
    if (supported) speechSynthesis.cancel();
  }, []);

  /** False only once voices have loaded and none match. */
  const hasVoice = useCallback(
    (bcp47: string | undefined) => !!bcp47 && (voices.length === 0 || !!pickVoice(voices, bcp47)),
    [voices],
  );

  return { supported, speak, cancel, hasVoice };
}
