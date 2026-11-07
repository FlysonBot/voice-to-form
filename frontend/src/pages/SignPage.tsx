import { useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { fillForm } from '../api/client';
import ProgressSteps from '../components/layout/ProgressSteps';
import SignaturePad, { type SignaturePadHandle } from '../components/sign/SignaturePad';
import { formName } from '../forms';
import { useT } from '../i18n/strings';
import { useAppStore } from '../store/profileStore';

/** Step 5: sign on screen → POST /form/fill → the filled PDF. */
export default function SignPage() {
  const t = useT();
  const navigate = useNavigate();
  const { formId = '' } = useParams();
  const { setSignature, setConfirmed } = useAppStore();
  const pad = useRef<SignaturePadHandle>(null);
  const [hasInk, setHasInk] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(false);

  async function finish() {
    const png = pad.current?.toBase64();
    if (!png) return;
    setSignature(png);
    setConfirmed(true);
    setBusy(true);
    setError(false);
    try {
      const pdf = await fillForm(useAppStore.getState().session, formId);
      navigate(`/form/${formId}/done`, { state: { pdfUrl: URL.createObjectURL(pdf) } });
    } catch {
      setError(true);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto max-w-3xl px-4 py-6">
      <ProgressSteps current={4} />
      <p className="text-sm font-medium text-stone-500">{formName(formId)}</p>
      <h1 className="mt-2 text-3xl font-bold tracking-tight">✍️ {t('signTitle')}</h1>
      <p className="mt-2 text-stone-600">{t('signIntro')}</p>

      <div className="mt-6">
        <SignaturePad ref={pad} onChange={setHasInk} label={t('signTitle')} />
        <div className="mt-2 flex justify-end">
          <button onClick={() => pad.current?.clear()} className="rounded-lg px-4 py-2 text-sm font-medium text-stone-600 ring-1 ring-stone-300 hover:bg-stone-50">
            {t('clear')}
          </button>
        </div>
      </div>

      {error && <p role="alert" className="mt-4 rounded-lg bg-red-50 px-4 py-3 text-red-800">{t('chatError')}</p>}
      <button
        onClick={finish}
        disabled={!hasInk || busy}
        className="mt-6 min-h-14 w-full rounded-xl bg-teal-700 text-lg font-semibold text-white hover:bg-teal-800 disabled:opacity-40"
      >
        {busy ? t('creatingPdf') : t('signAndFinish')}
      </button>
      <p className="mt-4 text-sm text-stone-500">{t('trust')}</p>
    </main>
  );
}
