import { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { formGaps, voiceAnswer, voiceQuestion } from '../api/client';
import ChatInput from '../components/chat/ChatInput';
import ProgressSteps from '../components/layout/ProgressSteps';
import VoiceToggle from '../components/voice/VoiceToggle';
import { formatValue, labelFor } from '../fields';
import { formName } from '../forms';
import { useListener } from '../hooks/useListener';
import { useReplyPlayer } from '../hooks/useReplyPlayer';
import { useLanguage, useT } from '../i18n/strings';
import { useAppStore } from '../store/profileStore';

type Phase = 'loading' | 'asking' | 'asking-followup' | 'parsing' | 'heard' | 'error';

/**
 * Step 3: ask, by voice, only what THIS form needs that the profile doesn't have
 * (POST /form/gaps → /voice/question → /voice/answer). Never re-asks profile data.
 */
export default function GapsPage() {
  const t = useT();
  const navigate = useNavigate();
  const { formId = '' } = useParams();
  const { speechLocale: bcp47 } = useLanguage();
  const { session, voiceOn, setVoiceOn, setMissingFields, mergeProfile } = useAppStore();
  const [idx, setIdx] = useState(0);
  const [phase, setPhase] = useState<Phase>('loading');
  const [question, setQuestion] = useState('');
  const [heard, setHeard] = useState<{ transcript: string; value: unknown } | null>(null);
  const fields = session.missing_fields;
  const field = fields[idx];

  const player = useReplyPlayer();
  const listener = useListener(bcp47, (text, audio) => latest.current.answer(text, audio));
  const latest = useRef({ answer: (_t: string, _a: Blob | null) => {} });
  useEffect(() => {
    latest.current = { answer };
  });

  // 1) Which fields does this form still need?
  useEffect(() => {
    formGaps(useAppStore.getState().session, formId)
      .then((r) => {
        setMissingFields(r.missing_fields ?? []);
        setIdx(0);
        setPhase('asking');
      })
      .catch(() => setPhase('error'));
  }, [formId, setMissingFields]);

  // 2) Ask the current question out loud, then open the mic
  useEffect(() => {
    if (phase !== 'asking') return;
    if (!field) {
      navigate(`/form/${formId}/review`, { replace: true });
      return;
    }
    let cancelled = false;
    setHeard(null);
    voiceQuestion(useAppStore.getState().session, field)
      .then((q) => {
        if (cancelled) return;
        setQuestion(q.text);
        player.play('q', q.text, bcp47, !useAppStore.getState().voiceOn, () => listener.supported && listener.start(), q);
      })
      .catch(() => !cancelled && setPhase('error'));
    return () => {
      cancelled = true;
    };
    // player/listener are stable enough; re-run only when the question changes
    // oxlint-disable-next-line react-hooks/exhaustive-deps
  }, [phase, field, formId]);

  // 3) Turn the spoken (or typed) answer into a value
  async function answer(text: string, audio: Blob | null) {
    if (!field) return;
    player.stop();
    setPhase('parsing');
    try {
      const res = await voiceAnswer(useAppStore.getState().session, field, audio, text || null);
      // Gemini wasn't sure what it heard: ask its follow-up question instead of saving a guess
      if (res.status === 'unclear') {
        const q = res.clarification_question || t('rejectedRetry').replace('{field}', labelFor(field, t).toLowerCase());
        setQuestion(q);
        setPhase('asking-followup');
        player.play('q', q, bcp47, !useAppStore.getState().voiceOn, () => listener.supported && listener.start());
        return;
      }
      mergeProfile({ [field]: { value: res.value ?? null, confidence: Number(res.confidence) || 0, source: 'gap_voice' } });
      setHeard({ transcript: res.transcript || text, value: res.value });
      setPhase('heard');
    } catch {
      setPhase('error');
    }
  }

  function next() {
    listener.abort();
    player.stop();
    setIdx((i) => i + 1);
    setPhase('asking');
  }

  function leaveBlank() {
    // Empty value = the user will write it on the paper form; the recap says so
    mergeProfile({ [field]: { value: '', confidence: 1, source: 'gap_voice' } });
    next();
  }

  function again() {
    listener.abort();
    setPhase('asking');
  }

  return (
    <main className="mx-auto max-w-3xl px-4 py-6">
      <ProgressSteps current={2} />
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-medium text-stone-500">{formName(formId)}</p>
        <VoiceToggle on={voiceOn} onToggle={() => { if (voiceOn) player.finishNow(); setVoiceOn(!voiceOn); }} />
      </div>
      <h1 className="mt-2 text-3xl font-bold tracking-tight">{t('gapsTitle')}</h1>
      <p className="mt-2 text-stone-600">{t('gapsIntro')}</p>

      {phase === 'loading' && <p role="status" className="mt-8 text-stone-500">{t('loading')}</p>}
      {phase === 'error' && (
        <div className="mt-8 rounded-xl bg-red-50 p-4 text-red-800">
          {t('chatError')}{' '}
          <button onClick={() => setPhase(field ? 'asking' : 'loading')} className="font-semibold underline">{t('sayAgain')}</button>
        </div>
      )}

      {field && phase !== 'loading' && phase !== 'error' && (
        <section className="mt-6 overflow-hidden rounded-2xl bg-white shadow-sm ring-1 ring-stone-200">
          <div className="p-6">
            <p className="text-sm font-medium text-teal-800">
              {idx + 1} / {fields.length} · {labelFor(field, t)}
            </p>
            <p dir="auto" className="mt-2 min-h-16 text-2xl font-medium leading-snug" aria-live="polite">
              {player.anim ? question.slice(0, player.anim.shown) : question}
            </p>

            {listener.listening && (
              <p dir="auto" className="mt-4 rounded-xl bg-teal-50 px-4 py-3 text-lg text-teal-900">
                <span className="me-2 inline-block h-2.5 w-2.5 animate-pulse rounded-full bg-red-500 align-middle" aria-hidden />
                {listener.interim || t('listening')}
              </p>
            )}
            {phase === 'parsing' && <p role="status" className="mt-4 text-stone-500">{t('loading')}</p>}
            {phase === 'heard' && heard && (
              <div className="mt-4 rounded-xl bg-stone-50 p-4 ring-1 ring-stone-200">
                <p className="text-sm text-stone-500">{t('heardYou')}</p>
                <p dir="auto" className="mt-1 text-xl font-semibold">{formatValue(heard.value) || heard.transcript || '—'}</p>
                <div className="mt-4 flex flex-wrap gap-2">
                  <button onClick={next} className="min-h-12 rounded-xl bg-teal-700 px-6 font-semibold text-white hover:bg-teal-800">{t('continue')} →</button>
                  <button onClick={again} className="min-h-12 rounded-xl px-5 font-medium text-stone-700 ring-1 ring-stone-300 hover:bg-stone-50">🎤 {t('sayAgain')}</button>
                </div>
              </div>
            )}
          </div>

          {(phase === 'asking' || phase === 'asking-followup') && (
            <>
              <ChatInput
                onSend={(text) => answer(text, null)}
                disabled={false}
                micAvailable={listener.supported}
                listening={listener.listening}
                onMic={() => (listener.listening ? listener.stop() : (player.stop(), listener.start()))}
              />
              <div className="border-t border-stone-100 bg-stone-50 px-4 py-3">
                <button onClick={leaveBlank} className="min-h-11 rounded-lg px-4 font-medium text-stone-700 ring-1 ring-stone-300 hover:bg-white">
                  {t('leaveBlank')}
                </button>
                <span className="ms-3 text-sm text-stone-500">{t('leaveBlankNote')}</span>
              </div>
            </>
          )}
        </section>
      )}
    </main>
  );
}
