import { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { recap, voiceAnswer } from '../api/client';
import ProgressSteps from '../components/layout/ProgressSteps';
import VoiceToggle from '../components/voice/VoiceToggle';
import { CONFIDENCE_THRESHOLD, formatValue, isEditable, labelFor, FIELD_LABELS } from '../fields';
import { formName } from '../forms';
import { useListener } from '../hooks/useListener';
import { useReplyPlayer } from '../hooks/useReplyPlayer';
import { useLanguage, useT } from '../i18n/strings';
import { useAppStore } from '../store/profileStore';
import type { RecapResponse } from '../types';

/** Step 4: read everything back in the user's language; yellow = confirm before signing (POST /recap). */
export default function ReviewPage() {
  const t = useT();
  const navigate = useNavigate();
  const { formId = '' } = useParams();
  const { speechLocale: bcp47 } = useLanguage();
  const { session, confirmedFields, voiceOn, setVoiceOn, confirmField, setFieldValue, mergeProfile } = useAppStore();
  const [data, setData] = useState<RecapResponse | null>(null);
  const [error, setError] = useState(false);
  const [editing, setEditing] = useState<{ field: string; text: string } | null>(null);
  const [voiceField, setVoiceField] = useState<string | null>(null);
  const player = useReplyPlayer();
  const listener = useListener(bcp47, (text, audio) => latest.current.reanswer(text, audio));
  const latest = useRef({ reanswer: (_t: string, _a: Blob | null) => {} });
  useEffect(() => {
    latest.current = { reanswer };
  });

  useEffect(() => {
    recap(useAppStore.getState().session)
      .then((r) => {
        setData(r);
        // Read it aloud once on arrival
        player.play('recap', r.text, bcp47, !useAppStore.getState().voiceOn, undefined, r);
      })
      .catch(() => setError(true));
    // oxlint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Rows: the recap's order, plus fields the user chose to leave blank. Values come from the
  // live profile so edits show immediately.
  const rows = (data?.items ?? []).map((i) => i.field);
  for (const f of session.missing_fields) if (!rows.includes(f)) rows.push(f);
  const recapLabel = (f: string) => data?.items.find((i) => i.field === f)?.label;
  const valueOf = (f: string) => session.profile[f]?.value ?? data?.items.find((i) => i.field === f)?.value;
  const isYellow = (f: string) => {
    const v = valueOf(f);
    if (v === null || v === undefined || v === '' || confirmedFields.includes(f)) return false;
    const p = session.profile[f];
    return p ? p.confidence < CONFIDENCE_THRESHOLD : !!data?.items.find((i) => i.field === f)?.needs_confirm;
  };
  const yellowLeft = rows.filter(isYellow).length;

  async function reanswer(text: string, audio: Blob | null) {
    const field = voiceField;
    if (!field) return;
    try {
      const res = await voiceAnswer(useAppStore.getState().session, field, audio, text || null);
      mergeProfile({ [field]: { value: res.value ?? null, confidence: Number(res.confidence) || 0, source: 'gap_voice' } });
    } finally {
      setVoiceField(null);
    }
  }

  function sayAgain(field: string) {
    player.stop();
    listener.abort();
    setVoiceField(field);
    listener.start();
  }

  return (
    <main className="mx-auto max-w-3xl px-4 py-6">
      <ProgressSteps current={3} />
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-medium text-stone-500">{formName(formId)}</p>
        <VoiceToggle on={voiceOn} onToggle={() => { if (voiceOn) player.finishNow(); setVoiceOn(!voiceOn); }} />
      </div>
      <h1 className="mt-2 text-3xl font-bold tracking-tight">{t('reviewTitle')}</h1>
      <p className="mt-2 text-stone-600">{t('reviewIntro')}</p>

      {data && (
        <div className="mt-4 rounded-xl bg-teal-50 p-4">
          <p dir="auto" className="leading-relaxed text-teal-950">{player.anim ? data.text.slice(0, player.anim.shown) : data.text}</p>
          <button
            onClick={() => player.play('recap', data.text, bcp47, false, undefined, data)}
            className="mt-2 text-sm font-semibold text-teal-800 underline"
          >
            🔊 {t('readAloud')}
          </button>
        </div>
      )}
      {!data && !error && <p role="status" className="mt-6 text-stone-500">{t('loading')}</p>}
      {error && <p role="alert" className="mt-6 text-red-700">{t('chatError')}</p>}

      <ul className="mt-6 space-y-2">
        {rows.map((f) => {
          const v = valueOf(f);
          const blank = v === null || v === undefined || v === '';
          const yellow = isYellow(f);
          const label = FIELD_LABELS[f] ? labelFor(f, t) : (recapLabel(f) ?? labelFor(f, t));
          return (
            <li key={f} className={`rounded-xl p-4 ring-1 ${yellow ? 'bg-amber-50 ring-amber-300' : 'bg-white ring-stone-200'}`}>
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-stone-500">{label}</p>
                  {editing?.field === f ? (
                    <form
                      className="mt-1 flex gap-2"
                      onSubmit={(e) => { e.preventDefault(); setFieldValue(f, editing.text.trim()); setEditing(null); }}
                    >
                      <input
                        autoFocus
                        dir="auto"
                        value={editing.text}
                        onChange={(e) => setEditing({ field: f, text: e.target.value })}
                        className="min-h-11 min-w-0 flex-1 rounded-lg border border-stone-300 px-3 text-base"
                      />
                      <button type="submit" className="rounded-lg bg-teal-700 px-4 font-medium text-white">{t('save')}</button>
                      <button type="button" onClick={() => setEditing(null)} className="rounded-lg px-3 text-stone-600">{t('cancel')}</button>
                    </form>
                  ) : voiceField === f ? (
                    <p className="mt-1 text-lg text-teal-900">
                      <span className="me-2 inline-block h-2.5 w-2.5 animate-pulse rounded-full bg-red-500 align-middle" aria-hidden />
                      {listener.interim || t('listening')}
                    </p>
                  ) : blank ? (
                    <p className="mt-1 font-medium italic text-stone-500">{t('blankField')}</p>
                  ) : (
                    <p dir="auto" className="mt-1 break-words text-lg font-semibold">{formatValue(v) || '—'}</p>
                  )}
                </div>
                {editing?.field !== f && voiceField !== f && (
                  <div className="flex shrink-0 flex-wrap gap-1.5">
                    {yellow && (
                      <button onClick={() => confirmField(f)} className="min-h-10 rounded-lg bg-amber-400 px-3 text-sm font-semibold text-amber-950 hover:bg-amber-300">
                        ✓ {t('confirmIt')}
                      </button>
                    )}
                    {listener.supported && (
                      <button onClick={() => sayAgain(f)} aria-label={`${t('sayAgain')}: ${label}`} className="min-h-10 rounded-lg px-3 text-sm ring-1 ring-stone-300 hover:bg-stone-50">
                        🎤
                      </button>
                    )}
                    {isEditable(v) && (
                      <button
                        onClick={() => setEditing({ field: f, text: blank ? '' : String(v) })}
                        className="min-h-10 rounded-lg px-3 text-sm font-medium ring-1 ring-stone-300 hover:bg-stone-50"
                      >
                        {t('edit')}
                      </button>
                    )}
                  </div>
                )}
              </div>
              {voiceField === f && (
                <button onClick={() => listener.stop()} className="mt-2 text-sm font-semibold text-red-700 underline">{t('tapToStop')}</button>
              )}
            </li>
          );
        })}
      </ul>

      <div className="mt-8">
        {yellowLeft > 0 && <p className="mb-2 text-sm font-medium text-amber-800">{t('confirmYellowFirst')} ({yellowLeft})</p>}
        <button
          onClick={() => { player.stop(); navigate(`/form/${formId}/sign`); }}
          disabled={yellowLeft > 0 || !data}
          className="min-h-14 w-full rounded-xl bg-teal-700 text-lg font-semibold text-white hover:bg-teal-800 disabled:opacity-40"
        >
          {t('continue')} → {t('stepSign')}
        </button>
      </div>
    </main>
  );
}
