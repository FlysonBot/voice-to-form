import { useCallback, useEffect, useRef, useState } from 'react';
import type { SpokenText } from '../types';
import { useSpeaker } from './useSpeaker';

const TICK_MS = 30;
const CPS_SPOKEN = 15; // roughly matches speaking pace
const CPS_SILENT = 50; // text-only replies type out faster

export interface ReplyAnim {
  id: string;
  shown: number; // characters revealed so far
}

interface Run {
  token: number;
  timer: number;
  onDone?: () => void;
  audio?: HTMLAudioElement;
}

/**
 * Plays an assistant line: speaks it and types it out at the same time.
 * Uses Gemini TTS audio when the backend sends it, otherwise the browser's voice.
 */
export function useReplyPlayer() {
  const speaker = useSpeaker();
  const { speak, cancel } = speaker;
  const [anim, setAnim] = useState<ReplyAnim | null>(null);
  const run = useRef<Run | null>(null);
  const tokenRef = useRef(0);

  const clear = useCallback(() => {
    if (run.current) {
      window.clearInterval(run.current.timer);
      run.current.audio?.pause();
    }
    run.current = null;
    tokenRef.current++; // any late events from the old run become no-ops
    setAnim(null);
  }, []);

  /** Interrupt: stop audio and show the full text, without calling onDone. */
  const stop = useCallback(() => {
    clear();
    cancel();
  }, [clear, cancel]);

  /** Skip to the end: stop audio, show the full text, and call onDone. */
  const finishNow = useCallback(() => {
    const onDone = run.current?.onDone;
    if (!run.current) return;
    stop();
    onDone?.();
  }, [stop]);

  const play = useCallback(
    (id: string, text: string, bcp47: string | undefined, muted: boolean, onDone?: () => void, tts?: SpokenText) => {
      stop();
      const token = ++tokenRef.current;
      const live = () => tokenRef.current === token;

      let shown = 0;
      let typed = false;
      let spoken = true;
      let boundaryMode = false;
      let cps = CPS_SILENT;

      const complete = () => {
        if (!live() || !typed || !spoken) return;
        clear();
        onDone?.();
      };
      const reveal = (n: number) => {
        if (!live()) return;
        shown = Math.min(text.length, Math.max(shown, n));
        setAnim({ id, shown: Math.floor(shown) });
        if (shown >= text.length && !typed) {
          typed = true;
          window.clearInterval(timer);
          complete();
        }
      };
      const speechEnded = () => {
        if (!live()) return;
        spoken = true;
        reveal(text.length);
        complete();
      };
      const browserSpeak = () => {
        spoken = !speak(text, bcp47, {
          onBoundary: (i, len) => {
            boundaryMode = true;
            reveal(i + Math.max(len, 1));
          },
          onEnd: speechEnded,
        });
        cps = spoken ? CPS_SILENT : CPS_SPOKEN;
      };

      let audio: HTMLAudioElement | undefined;
      if (!muted && tts?.audio_b64) {
        // Gemini TTS: pace the typing to the clip's length; fall back to the browser voice on error
        spoken = false;
        cps = CPS_SPOKEN;
        audio = new Audio(`data:${tts.audio_mime || 'audio/wav'};base64,${tts.audio_b64}`);
        audio.onloadedmetadata = () => {
          if (audio && isFinite(audio.duration) && audio.duration > 0) cps = text.length / audio.duration;
        };
        audio.onended = speechEnded;
        audio.onerror = () => live() && browserSpeak();
        audio.play().catch(() => live() && browserSpeak());
      } else if (!muted) {
        browserSpeak();
      }

      const timer = window.setInterval(() => {
        if (!boundaryMode) reveal(shown + (cps * TICK_MS) / 1000);
      }, TICK_MS);

      run.current = { token, timer, onDone, audio };
      setAnim({ id, shown: 0 });
    },
    [stop, clear, speak],
  );

  // Leaving the page stops the audio
  useEffect(() => () => {
    if (run.current) {
      window.clearInterval(run.current.timer);
      run.current.audio?.pause();
    }
    tokenRef.current++; // so the cancelled speech's end event doesn't call onDone
    cancel();
  }, [cancel]);

  return { anim, play, stop, finishNow, speaker };
}
