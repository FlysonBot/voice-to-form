import { useCallback, useEffect, useRef, useState } from 'react';

// Minimal types: the Web Speech recognition API isn't in TypeScript's DOM lib
interface RecognitionResultList {
  length: number;
  [i: number]: { 0: { transcript: string }; isFinal: boolean };
}
interface Recognition {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  maxAlternatives: number;
  onresult: ((e: { results: RecognitionResultList }) => void) | null;
  onerror: ((e: { error: string }) => void) | null;
  onend: (() => void) | null;
  start(): void;
  stop(): void;
  abort(): void;
}
type RecognitionCtor = new () => Recognition;

const Ctor: RecognitionCtor | undefined =
  typeof window === 'undefined'
    ? undefined
    : ((window as unknown as Record<string, RecognitionCtor | undefined>).SpeechRecognition ??
       (window as unknown as Record<string, RecognitionCtor | undefined>).webkitSpeechRecognition);

const canRecord = typeof window !== 'undefined' && !!navigator.mediaDevices?.getUserMedia && typeof MediaRecorder !== 'undefined';

/** How long the user can pause mid-answer before we treat it as finished */
export const SILENCE_MS = 3500;
/** How long to wait for the first word before giving up */
const NO_SPEECH_MS = 8000;

export type ListenError = 'not-allowed' | 'language-not-supported' | 'other';

/**
 * Mic input. Records the audio (sent to Gemini to transcribe) and, where the browser supports it,
 * shows a live transcript and detects when the speaker has finished. onFinal gets both.
 */
export function useListener(bcp47: string | undefined, onFinal: (text: string, audio: Blob | null) => void) {
  const [listening, setListening] = useState(false);
  const [interim, setInterim] = useState('');
  const [error, setError] = useState<ListenError | null>(null);
  const rec = useRef<Recognition | null>(null);
  const recorder = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);
  const stream = useRef<MediaStream | null>(null);
  const silence = useRef(0);
  const text = useRef('');
  const finishing = useRef(false);
  const onFinalRef = useRef(onFinal);
  const abortRef = useRef<() => void>(() => {});
  useEffect(() => {
    onFinalRef.current = onFinal;
  });

  /** Mic works if we can record audio or the browser can transcribe */
  const supported = canRecord || !!Ctor;

  const releaseMic = () => {
    stream.current?.getTracks().forEach((tr) => tr.stop());
    stream.current = null;
  };

  // Called once both the recognizer and the recorder have stopped
  const finish = useCallback(() => {
    if (recorder.current && recorder.current.state !== 'inactive') return; // wait for recorder.onstop
    if (rec.current) return; // wait for recognition.onend
    window.clearTimeout(silence.current);
    const audio = chunks.current.length ? new Blob(chunks.current, { type: chunks.current[0].type || 'audio/webm' }) : null;
    chunks.current = [];
    recorder.current = null;
    releaseMic();
    setListening(false);
    setInterim('');
    const said = text.current.trim();
    text.current = '';
    if (finishing.current && (said || (audio && audio.size > 2000))) onFinalRef.current(said, audio);
    finishing.current = false;
  }, []);

  /** Stop listening and send what was heard. */
  const stop = useCallback(() => {
    finishing.current = true;
    window.clearTimeout(silence.current);
    if (rec.current) rec.current.stop();
    if (recorder.current?.state === 'recording') recorder.current.stop();
    finish();
  }, [finish]);

  const start = useCallback(async () => {
    if (rec.current || recorder.current) return;
    setError(null);
    setInterim('');
    text.current = '';
    finishing.current = false;
    setListening(true);

    // 1) Record audio for Gemini
    if (canRecord) {
      try {
        stream.current = await navigator.mediaDevices.getUserMedia({ audio: true });
        const mr = new MediaRecorder(stream.current);
        chunks.current = [];
        mr.ondataavailable = (e) => e.data.size && chunks.current.push(e.data);
        mr.onstop = () => finish();
        recorder.current = mr;
        mr.start();
      } catch (e) {
        setError((e as Error).name === 'NotAllowedError' ? 'not-allowed' : 'other');
        setListening(false);
        return;
      }
    }

    // 2) Live transcript + end-of-speech detection (Chrome, Edge, Safari)
    const armSilence = (ms: number, then: () => void) => {
      window.clearTimeout(silence.current);
      silence.current = window.setTimeout(then, ms);
    };
    if (Ctor && bcp47) {
      const r = new Ctor();
      r.lang = bcp47;
      r.interimResults = true;
      // Continuous so the browser doesn't cut people off after ~1s; our silence timer decides
      r.continuous = true;
      r.maxAlternatives = 1;
      r.onresult = (e) => {
        text.current = Array.from({ length: e.results.length }, (_, i) => e.results[i][0].transcript).join('');
        setInterim(text.current);
        armSilence(SILENCE_MS, stop);
      };
      r.onerror = (e) => {
        if (e.error === 'no-speech' || e.error === 'aborted') return;
        if (e.error === 'not-allowed' || e.error === 'service-not-allowed') setError('not-allowed');
        else if (e.error === 'language-not-supported') setError('language-not-supported');
      };
      r.onend = () => {
        rec.current = null;
        // Recognizer ended on its own (e.g. network): treat as finished speaking
        if (!finishing.current) finishing.current = true;
        if (recorder.current?.state === 'recording') recorder.current.stop();
        finish();
      };
      rec.current = r;
      try {
        r.start();
      } catch {
        rec.current = null;
      }
      armSilence(NO_SPEECH_MS, () => abortRef.current()); // nothing said: discard
    }
    // Without recognition (e.g. Firefox) the user taps the button again to stop
  }, [bcp47, finish, stop]);

  /** Stop listening and throw away what was heard. */
  const abort = useCallback(() => {
    finishing.current = false;
    window.clearTimeout(silence.current);
    const r = rec.current;
    rec.current = null;
    if (r) {
      r.onend = null;
      r.abort();
    }
    if (recorder.current?.state === 'recording') recorder.current.stop();
    recorder.current = null;
    chunks.current = [];
    releaseMic();
    setListening(false);
    setInterim('');
  }, []);

  useEffect(() => {
    abortRef.current = abort;
  }, [abort]);
  useEffect(() => abort, [abort]);

  return { supported, listening, interim, error, start, stop, abort };
}
