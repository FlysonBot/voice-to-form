import { useCallback, useEffect, useRef, useState } from "react";
import { releaseMic, startRecording } from "./recorder";
import { speak, stopSpeaking } from "./speaker";

/** status: "idle" | "speaking" | "listening" | "thinking" */
export function useVoice(language) {
  const [status, setStatus] = useState("idle");
  const [level, setLevel] = useState(0);
  const recRef = useRef(null);
  const aliveRef = useRef(true);

  // langOverride: speak in a language detected mid-turn, before the parent re-renders.
  const say = useCallback(async (text, langOverride) => {
    setStatus("speaking");
    try { await speak(text, langOverride || language); } finally { if (aliveRef.current) setStatus("idle"); }
  }, [language]);

  /** Records one answer. Resolves to audio payload, or null if nothing was heard. Throws if mic is blocked. */
  const listen = useCallback(async () => {
    stopSpeaking();
    setStatus("listening");
    try {
      const rec = await startRecording({ onLevel: setLevel });
      recRef.current = rec;
      return await rec.result;
    } finally {
      recRef.current = null;
      if (aliveRef.current) { setLevel(0); setStatus("idle"); }
    }
  }, []);

  const stopListening = useCallback(() => recRef.current?.stop(), []);
  const cancelAll = useCallback(() => { stopSpeaking(); recRef.current?.cancel(); }, []);

  useEffect(() => {
    aliveRef.current = true;
    return () => { aliveRef.current = false; stopSpeaking(); recRef.current?.cancel(); releaseMic(); };
  }, []);

  return { status, setStatus, level, say, listen, stopListening, cancelAll };
}
