import { useEffect, useRef, useState } from "react";
import { post } from "./api";
import { ui } from "./i18n";
import MicButton from "./MicButton";
import { useVoice } from "./useVoice";

/**
 * Reads every field back in the user's language. Low-confidence fields are yellow and
 * must be confirmed (by voice or the ✓ button) before "Everything is correct" unlocks.
 * Corrections: by voice ("my last name is with an S") or by tapping Edit (the only typing fallback).
 * Props: language, profile, formName, blankFields (e.g. ["citizenship_status"]), onProfile(p), onConfirm(p)
 */
export default function VoiceRecap({ language, profile, formName, blankFields = [], onProfile, onConfirm }) {
  const t = ui(language);
  const v = useVoice(language);
  const [recap, setRecap] = useState(null);
  const [confirmed, setConfirmed] = useState(new Set());
  const [editing, setEditing] = useState(null);
  const [editValue, setEditValue] = useState("");
  const [transcript, setTranscript] = useState("");
  const [error, setError] = useState("");
  const profileRef = useRef(profile);
  const pendingField = useRef(""); // set when the user said "X is wrong" without the new value

  useEffect(() => {
    let alive = true;
    (async () => {
      v.setStatus("thinking");
      try {
        const r = await post("/recap", { language, profile: profileRef.current, form_name: formName, blank_fields: blankFields });
        if (!alive) return;
        setRecap(r);
        await v.say(r.script);
      } catch (e) { if (alive) { v.setStatus("idle"); setError(e.message); } }
    })();
    return () => { alive = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function updateProfile(p) { profileRef.current = p; onProfile?.(p); }
  const markConfirmed = (field) => setConfirmed((s) => new Set(s).add(field));

  const unconfirmed = (recap?.needs_confirmation || []).filter((f) => !confirmed.has(f));
  const allDone = recap && unconfirmed.length === 0;

  async function listenForCorrection() {
    setError("");
    let audio;
    try { audio = await v.listen(); } catch { setError(t.micBlocked); return; }
    if (!audio) { setError(t.didntHear); return; }
    v.setStatus("thinking");
    let res;
    try {
      res = await post("/recap/correct", { language, profile: profileRef.current, current_field: pendingField.current, ...audio });
    } catch (e) { v.setStatus("idle"); setError(e.message); return; }
    setTranscript(res.transcript);
    updateProfile(res.profile);

    if (res.action === "correct" && res.field && !res.new_value) {
      pendingField.current = res.field;         // they said it's wrong; ask for the right value
      await v.say(res.reply);
      return listenForCorrection();
    }
    pendingField.current = "";
    if (res.action === "correct" || res.action === "confirm_field") {
      markConfirmed(res.field);
      setRecap((r) => ({
        ...r,
        items: r.items.map((it) => (it.field === res.field ? { ...it, value: res.profile[res.field]?.value, low_confidence: false } : it)),
      }));
      await v.say(res.reply);
    } else if (res.action === "confirm_all") {
      (recap?.needs_confirmation || []).forEach(markConfirmed);
      await v.say(res.reply);
    } else if (res.action === "repeat") {
      await v.say(recap.script);
    } else {
      await v.say(res.reply);
    }
  }

  function saveEdit(field) {
    const old = profileRef.current[field] || {};
    updateProfile({ ...profileRef.current, [field]: { ...old, value: editValue, confidence: 1, user_confirmed: true } });
    setRecap((r) => ({ ...r, items: r.items.map((it) => (it.field === field ? { ...it, value: editValue, low_confidence: false } : it)) }));
    markConfirmed(field);
    setEditing(null);
  }

  if (!recap) {
    return <div className="voice-screen">{error ? <div className="voice-error">{error}</div> : <div className="voice-question">{t.thinking}</div>}</div>;
  }

  return (
    <div className="voice-screen">
      <div className="voice-question">{recap.intro}</div>
      <ul className="recap-list">
        {recap.items.map((it) => {
          const yellow = it.low_confidence && !confirmed.has(it.field);
          return (
            <li key={it.field} className={yellow ? "recap-item low" : "recap-item"}>
              <div className="recap-label">{it.label}{yellow && <span className="recap-flag"> ⚠ {t.notSure}</span>}</div>
              {editing === it.field ? (
                <div className="recap-edit">
                  <input value={editValue} onChange={(e) => setEditValue(e.target.value)} autoFocus />
                  <button onClick={() => saveEdit(it.field)}>{t.save}</button>
                </div>
              ) : (
                <div className="recap-value">
                  {formatValue(it.value)}
                  <span className="recap-buttons">
                    <button onClick={() => v.say(it.spoken)} aria-label={t.repeat}>🔊</button>
                    {yellow && <button onClick={() => markConfirmed(it.field)}>✓ {t.isCorrect}</button>}
                    {!Array.isArray(it.value) && (
                      <button onClick={() => { setEditing(it.field); setEditValue(String(it.value ?? "")); }}>✏️ {t.edit}</button>
                    )}
                  </span>
                </div>
              )}
            </li>
          );
        })}
      </ul>
      <div className="voice-question small">{recap.outro}</div>
      {transcript && <div className="voice-transcript">{t.youSaid}: “{transcript}”</div>}
      {error && <div className="voice-error" role="alert">{error}</div>}

      <MicButton status={v.status} level={v.level} language={language}
        onListen={listenForCorrection} onStop={v.stopListening}
        onInterrupt={() => { v.cancelAll(); listenForCorrection(); }} />

      <div className="voice-actions">
        <button onClick={() => v.say(recap.script)} disabled={v.status !== "idle"}>🔁 {t.repeat}</button>
        <button className="big-btn" disabled={!allDone} onClick={() => onConfirm?.(profileRef.current)}>✅ {t.allCorrect}</button>
      </div>
    </div>
  );
}

function formatValue(v) {
  if (Array.isArray(v)) return v.map((m) => [m.first_name, m.relationship, m.date_of_birth].filter(Boolean).join(", ")).join(" · ");
  if (typeof v === "boolean") return v ? "✓" : "✗";
  return String(v);
}
