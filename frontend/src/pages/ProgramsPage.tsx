import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { findPrograms } from '../api/client';
import ProgressSteps from '../components/layout/ProgressSteps';
import { isFormReady } from '../forms';
import { useT } from '../i18n/strings';
import { useAppStore } from '../store/profileStore';

/** Path B: programs the user MAY qualify for (POST /programs/find, grounded in official sources). */
export default function ProgramsPage() {
  const t = useT();
  const navigate = useNavigate();
  const { session, setPrograms, selectForm } = useAppStore();
  const [state, setState] = useState<'loading' | 'ok' | 'error'>(session.suggested_programs.length ? 'ok' : 'loading');

  useEffect(() => {
    if (session.suggested_programs.length) return;
    findPrograms(useAppStore.getState().session)
      .then((r) => {
        setPrograms(r.suggested_programs ?? []);
        setState('ok');
      })
      .catch(() => setState('error'));
  }, [session.suggested_programs.length, setPrograms]);

  return (
    <main className="mx-auto max-w-3xl px-4 py-6">
      <ProgressSteps current={1} />
      <Link to="/choose" className="text-sm font-medium text-teal-800 hover:underline">
        <span aria-hidden className="inline-block rtl:-scale-x-100">←</span> {t('back')}
      </Link>
      <h1 className="mt-3 text-3xl font-bold tracking-tight">{t('programsTitle')}</h1>
      <p className="mt-2 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-900">{t('programsDisclaimer')}</p>

      {state === 'loading' && <p role="status" className="mt-8 text-stone-500">🔎 {t('searching')}</p>}
      {state === 'error' && <p role="alert" className="mt-8 text-red-700">{t('chatError')}</p>}

      <ul className="mt-6 space-y-4">
        {session.suggested_programs.map((p) => {
          const fillable = !!p.form_id && isFormReady(p.form_id);
          return (
            <li key={p.name} className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-stone-200">
              <h2 className="text-xl font-semibold">{p.name}</h2>
              <p dir="auto" className="mt-2 leading-relaxed text-stone-700">{p.why}</p>
              <a href={p.source_url} target="_blank" rel="noreferrer" className="mt-3 inline-block break-all text-sm font-medium text-teal-800 underline">
                {t('officialSource')}: {p.source_url.replace(/^https?:\/\//, '')} ↗
              </a>
              {fillable ? (
                <button
                  onClick={() => { selectForm(p.form_id!); navigate(`/form/${p.form_id}/questions`); }}
                  className="mt-4 block min-h-12 w-full rounded-xl bg-teal-700 px-5 font-semibold text-white hover:bg-teal-800 sm:w-auto"
                >
                  {t('fillThisForm')} →
                </button>
              ) : (
                <p className="mt-3 text-sm text-stone-500">{t('notFillableYet')}</p>
              )}
            </li>
          );
        })}
      </ul>
    </main>
  );
}
