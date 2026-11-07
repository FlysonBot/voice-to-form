import { Link, useNavigate } from 'react-router-dom';
import ProgressSteps from '../components/layout/ProgressSteps';
import { SUPPORTED_FORMS } from '../forms';
import { useT } from '../i18n/strings';
import { useAppStore } from '../store/profileStore';

/** Step 2: A) pick a supported form, or B) find forms I may qualify for. */
export default function ChoosePage() {
  const t = useT();
  const navigate = useNavigate();
  const selectForm = useAppStore((s) => s.selectForm);

  function fill(formId: string) {
    selectForm(formId);
    navigate(`/form/${formId}/questions`);
  }

  return (
    <main className="mx-auto max-w-4xl px-4 py-6">
      <ProgressSteps current={1} />
      <h1 className="text-3xl font-bold tracking-tight">{t('whatNext')}</h1>

      <div className="mt-6 grid gap-4 md:grid-cols-2">
        {/* Path B */}
        <Link
          to="/programs"
          className="group flex flex-col rounded-2xl bg-teal-700 p-6 text-white transition hover:bg-teal-800 focus:outline-none focus-visible:ring-4 focus-visible:ring-teal-200"
        >
          <span aria-hidden className="mb-4 flex h-14 w-14 items-center justify-center rounded-xl bg-white/15 text-3xl">🔎</span>
          <span className="text-2xl font-semibold">{t('findBenefitsTitle')}</span>
          <span className="mt-2 flex-1 leading-relaxed text-teal-50">{t('findFormsDesc')}</span>
          <span aria-hidden className="mt-4 text-2xl rtl:-scale-x-100">→</span>
        </Link>

        {/* Path A */}
        <section className="rounded-2xl bg-white p-6 ring-1 ring-stone-200">
          <span aria-hidden className="mb-4 flex h-14 w-14 items-center justify-center rounded-xl bg-teal-50 text-3xl">📄</span>
          <h2 className="text-2xl font-semibold">{t('haveFormTitle')}</h2>
          <p className="mt-2 leading-relaxed text-stone-600">{t('haveFormDesc')}</p>
          <ul className="mt-4 space-y-2">
            {SUPPORTED_FORMS.map((f) => (
              <li key={f.id}>
                <button
                  onClick={() => fill(f.id)}
                  disabled={!f.ready}
                  className="flex min-h-14 w-full items-center justify-between gap-3 rounded-xl px-4 text-start ring-1 ring-stone-200 hover:bg-teal-50 hover:ring-teal-400 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:bg-transparent disabled:hover:ring-stone-200"
                >
                  <span>
                    <span className="block font-semibold">{f.name}</span>
                    <span className="block text-xs text-stone-500">{f.agency}</span>
                  </span>
                  <span className="shrink-0 text-sm font-medium text-teal-800">{f.ready ? `${t('fillThisForm')} →` : t('comingSoon')}</span>
                </button>
              </li>
            ))}
            <li className="px-1 pt-1 text-sm text-stone-400">⬆ {t('uploadSoon')}</li>
          </ul>
        </section>
      </div>

      <p className="mt-6 rounded-xl bg-stone-100 px-4 py-3 text-sm text-stone-600">⚖️ {t('immigrationNote')}</p>
      <p className="mt-4 text-sm text-stone-500">🔒 {t('noStore')} {t('trust')}</p>
    </main>
  );
}
