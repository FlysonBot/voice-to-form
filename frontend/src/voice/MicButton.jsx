import { ui } from "./i18n";

/** Big always-visible mic. Tap while listening = done talking; tap while speaking = interrupt and answer. */
export default function MicButton({ status, level, language, onListen, onStop, onInterrupt, disabled }) {
  const t = ui(language);
  const label = { idle: t.tapToTalk, listening: t.listening, thinking: t.thinking, speaking: t.speaking }[status];
  const onClick = () => {
    if (status === "listening") onStop();
    else if (status === "speaking") onInterrupt();
    else if (status === "idle") onListen();
  };
  return (
    <div className="mic-wrap">
      <button
        className={`mic-btn mic-${status}`}
        onClick={onClick}
        disabled={disabled || status === "thinking"}
        aria-label={label}
        style={{ "--level": status === "listening" ? level : 0 }}
      >
        <span className="mic-ring" />
        <span className="mic-icon" aria-hidden>
          {status === "thinking" ? "⏳" : status === "speaking" ? "🔊" : "🎤"}
        </span>
      </button>
      <div className="mic-label" aria-live="polite">{label}</div>
    </div>
  );
}
