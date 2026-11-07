import { useEffect, useRef, useState } from "react";
import { post } from "./api";
import { ui } from "./i18n";
import MicButton from "./MicButton";
import { useVoice } from "./useVoice";

/**
 * Asks ONLY the form-specific fields the profile doesn't have (from /form/gaps).
 * Props:
 *  language, profile, formName
 *  missingFields   ["sdge_account_number", ...]  or  [{field, description}, ...]
 *  onProfile(p), onDone(p)
 * Handles: answer, skip / "leave it blank", "repeat", unclear (re-asks more simply),
 * and "that's wrong" (goes back to the previous field).
 */
export default function GapQuestions({ language, profile, formName, missingFields, onProfile, onDone }) {
  const t = ui(language);
  const v = useVoice(language);
  const fields = missingFields.map((f) => (typeof f === "string" ? { field: f, description: "" } : f));
  const [idx, setIdx] = useState(0);
  const [question, setQuestion] = useState("");
  const [transcript, setTranscript] = useState("");
  const [error, setError] = useState("");
  const profileRef = useRef(profile);
  const runId = useRef(0);

  useEffect(() => {
    if (fields.length === 0) { onDone?.(profileRef.current); return; }
    if (idx >= fields.length) { onDone?.(profileRef.current); return; }
    askField(idx);
    return () => { runId.current++; v.cancelAll(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idx]);

  function setEntry(field, entry) {
    profileRef.current = { ...profileRef.current, [field]: entry };
    onProfile?.(profileRef.current);
  }

  async function askField(i, retryReason = "") {
    const myRun = ++runId.current;
    const alive = () => runId.current === myRun;
    const { field, description } = fields[i];
    setError(""); setTranscript("");
    v.setStatus("thinking");
    let q;
    try {
      q = (await post("/voice/question", { language, field, description, form_name: formName, retry_reason: retryReason })).question;
    } catch (e) { v.setStatus("idle"); setError(e.message); return; }
    if (!alive()) return;
    setQuestion(q);
    await v.say(q);

    for (let attempt = 0; attempt < 4 && alive(); attempt++) {
      let audio;
      try { audio = await v.listen(); } catch { setError(t.micBlocked); return; }
      if (!alive()) return;
      if (!audio) { setError(t.didntHear); return; } // mic button restarts via listenAgain()

      v.setStatus("thinking");
      let res;
      try {
        res = await post("/voice/answer", { language, field, description, question: q, ...audio });
      } catch (e) { v.setStatus("idle"); setError(e.message); return; }
      if (!alive()) return;
      setTranscript(res.transcript);

      switch (res.intent) {
        case "answer":
        case "skip":
        case "leave_blank":
          if (res.profile_entry) setEntry(field, res.profile_entry);
          await v.say(res.reply);
          if (alive()) setIdx(i + 1);
          return;
        case "wrong":
          await v.say(res.reply);
          if (alive()) (i > 0 ? setIdx(i - 1) : askField(i));
          return;
        case "repeat":
          await v.say(q);
          break;
        default: // unclear
          if (attempt >= 1) return askField(i, "the user didn't understand or we couldn't hear them");
          await v.say(res.reply);
      }
    }
  }

  // Mic tapped while idle (e.g. after "didn't hear") -> re-run the current field's listen.
  const listenAgain = () => askField(idx);

  if (idx >= fields.length) return null;
  return (
    <div className="voice-screen">
      <div className="voice-progress">{t.question} {idx + 1} / {fields.length}</div>
      <div className="voice-question" aria-live="polite">{question || "…"}</div>
      {transcript && <div className="voice-transcript">{t.youSaid}: “{transcript}”</div>}
      {error && <div className="voice-error" role="alert">{error} <button onClick={listenAgain}>{t.tryAgain}</button></div>}

      <MicButton status={v.status} level={v.level} language={language}
        onListen={listenAgain} onStop={v.stopListening} onInterrupt={() => v.cancelAll()} />

      <div className="voice-actions">
        <button onClick={() => v.say(question)} disabled={v.status !== "idle"}>🔁 {t.repeat}</button>
        <button onClick={() => { setEntry(fields[idx].field, { value: null, confidence: 1, source: "gap_voice", skipped: true }); setIdx(idx + 1); }}>
          ⏭ {t.skip}
        </button>
        {idx > 0 && <button onClick={() => setIdx(idx - 1)}>↩ {t.goBack}</button>}
      </div>
    </div>
  );
}
