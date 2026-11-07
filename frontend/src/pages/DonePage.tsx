import { Link, Navigate, useLocation, useNavigate, useParams } from 'react-router-dom';
import { formName } from '../forms';
import { useT } from '../i18n/strings';
import { useAppStore } from '../store/profileStore';

/** Final screen: preview + download. Nothing is kept; "Start over" wipes the session. */
export default function DonePage() {
  const t = useT();
  const navigate = useNavigate();
  const { formId = '' } = useParams();
  const pdfUrl = (useLocation().state as { pdfUrl?: string } | null)?.pdfUrl;
  const { reset, selectForm } = useAppStore();

  if (!pdfUrl) return <Navigate to="/choose" replace />;

  return (
    <main className="mx-auto max-w-4xl px-4 py-6">
      <h1 className="text-3xl font-bold tracking-tight">✅ {t('doneTitle')}</h1>
      <p className="mt-2 text-stone-600">{formName(formId)} — {t('doneIntro')}</p>

      <a
        href={pdfUrl}
        download={`${formId}-filled.pdf`}
        className="mt-6 inline-flex min-h-14 items-center gap-2 rounded-xl bg-teal-700 px-8 text-lg font-semibold text-white hover:bg-teal-800"
      >
        ⬇ {t('download')}
      </a>

      <iframe src={pdfUrl} title={formName(formId)} className="mt-6 h-[70vh] w-full rounded-xl bg-white ring-1 ring-stone-200" />

      <p className="mt-6 rounded-xl bg-teal-50 px-4 py-3 font-medium text-teal-900">🔒 {t('noStoreLong')}</p>
      <div className="mt-4 flex flex-wrap gap-3">
        <Link to="/choose" onClick={() => selectForm(null)} className="min-h-12 rounded-xl px-5 py-3 font-medium ring-1 ring-stone-300 hover:bg-stone-50">
          {t('fillAnother')}
        </Link>
        <button
          onClick={() => { URL.revokeObjectURL(pdfUrl); reset(); navigate('/'); }}
          className="min-h-12 rounded-xl px-5 font-medium text-red-700 ring-1 ring-red-200 hover:bg-red-50"
        >
          {t('startOver')}
        </button>
      </div>
    </main>
  );
}
