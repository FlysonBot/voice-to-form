import { useRef, useState } from "react";
import { post } from "./api";
import { ui } from "./i18n";
import MicButton from "./MicButton";
import { useVoice } from "./useVoice";

/**
 * Voice onboarding conversation.
 * Props:
 *  language        "es" | "en" | ...
 *  profile         current profile object (shared format)
 *  onProfile(p)    called after every turn with the updated profile
 *  onDone(p)       called when every onboarding field is filled or skipped
 *  onScanRequest() optional: opens the camera + /profile/extract (Person 2/4) and
 *                  resolves to the updated profile, or null if cancelled
 */
export default function VoiceOnboarding({ language, profile, onProfile, onDone, onScanRequest }) {
  const t = ui(language);
  const v = useVoice(language);
  const [started, setStarted] = useState(false);
  const [question, setQuestion] = useState("");
  const [transcript, setTranscript] = useState("");
  const [error, setError] = useState("");
  const profileRef = useRef(profile || {});
  const questionRef = useRef("");
  const lastRequest = useRef(null);

  async function turn({ audio = null, userText = null } = {}) {
    setError("");
    v.setStatus("thinking");
    const body = {
      language,
      profile: profileRef.current,
      audio_b64: audio?.audio_b64 ?? null,
      mime_type: audio?.mime_type ?? "audio/wav",
      last_question: questionRef.current,
      user_text: userText,
    };
    lastRequest.current = body;
    let res;
    try {
      res = await post("/onboarding/turn", body);
    } catch (e) {
      v.setStatus("idle");
      setError(e.message);
      return;
    }
    profileRef.current = res.profile;
    onProfile?.(res.profile);
    setTranscript(res.transcript || "");
    setQuestion(res.say);
    questionRef.current = res.say;
    await v.say(res.say);
    if (res.done) return onDone?.(res.profile);
    await listenAndSend(); // natural back-and-forth: start listening right after the question
  }

  async function listenAndSend() {
    let audio;
    try {
      audio = await v.listen();
    } catch {
      setError(t.micBlocked);
      return;
    }
    if (!audio) { setError(t.didntHear); return; } // they can tap the mic to try again
    await turn({ audio });
  }

  async function retry() {
    if (lastRequest.current?.audio_b64) {
      const { audio_b64, mime_type } = lastRequest.current;
      return turn({ audio: { audio_b64, mime_type } });
    }
    return turn();
  }

  async function scan() {
    if (!onScanRequest) return;
    v.cancelAll();
    const updated = await onScanRequest();
    if (!updated) return;
    profileRef.current = updated;
    onProfile?.(updated);
    await turn({ userText: "I scanned a document. Briefly say thanks and continue with what is still missing." });
  }

  if (!started) {
    return (
      <div className="voice-screen">
        <p className="voice-note">🔒 {t.noStore}</p>
        <button className="big-btn" onClick={() => { setStarted(true); turn(); }}>{t.start} ▶</button>
      </div>
    );
  }

  return (
    <div className="voice-screen">
      <div className="voice-question" aria-live="polite">{question || "…"}</div>
      {transcript && <div className="voice-transcript">{t.youSaid}: “{transcript}”</div>}
      {error && (
        <div className="voice-error" role="alert">
          {error} <button onClick={retry}>{t.tryAgain}</button>
        </div>
      )}

      <MicButton
        status={v.status}
        level={v.level}
        language={language}
        onListen={listenAndSend}
        onStop={v.stopListening}
        onInterrupt={() => { v.cancelAll(); listenAndSend(); }}
      />

      <div className="voice-actions">
        <button onClick={() => v.say(questionRef.current)} disabled={v.status !== "idle"}>🔁 {t.repeat}</button>
        <button onClick={() => { v.cancelAll(); turn({ userText: "skip" }); }} disabled={v.status === "thinking"}>⏭ {t.skip}</button>
        {onScanRequest && <button onClick={scan} disabled={v.status === "thinking"}>📷 {t.scan}</button>}
      </div>
    </div>
  );
}
