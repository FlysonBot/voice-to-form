import { useRef, useState } from 'react';
import { extractFromPhoto } from '../../api/client';
import { useT, type Key } from '../../i18n/strings';
import { useAppStore } from '../../store/profileStore';

type DocType = 'id' | 'pay_stub' | 'bill';
const DOCS: { type: DocType; icon: string; label: Key }[] = [
  { type: 'id', icon: '🪪', label: 'scanId' },
  { type: 'pay_stub', icon: '💵', label: 'scanPayStub' },
  { type: 'bill', icon: '🧾', label: 'scanBill' },
];

/** "Skip questions with a photo": photograph an ID, pay stub or bill → /profile/extract. */
export default function DocScan({ onScanned }: { onScanned?: () => void }) {
  const t = useT();
  const mergeProfile = useAppStore((s) => s.mergeProfile);
  const input = useRef<HTMLInputElement>(null);
  const [docType, setDocType] = useState<DocType>('id');
  const [status, setStatus] = useState<'idle' | 'busy' | 'ok' | 'error'>('idle');

  function pick(type: DocType) {
    setDocType(type);
    input.current?.click();
  }

  async function onFile(file: File | undefined) {
    if (!file) return;
    setStatus('busy');
    try {
      const res = await extractFromPhoto(useAppStore.getState().session, file, docType);
      mergeProfile(res.fields ?? {});
      setStatus('ok');
      onScanned?.();
    } catch {
      setStatus('error');
    } finally {
      if (input.current) input.current.value = '';
    }
  }

  return (
    <div className="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-stone-200">
      <p className="mb-2 text-sm font-semibold text-stone-700">📷 {t('scanDoc')}</p>
      <div className="grid grid-cols-3 gap-2">
        {DOCS.map((d) => (
          <button
            key={d.type}
            onClick={() => pick(d.type)}
            disabled={status === 'busy'}
            className="flex min-h-16 flex-col items-center justify-center gap-1 rounded-xl bg-stone-50 px-2 text-xs font-medium text-stone-700 ring-1 ring-stone-200 hover:bg-teal-50 hover:ring-teal-300 disabled:opacity-50"
          >
            <span aria-hidden className="text-2xl">{d.icon}</span>
            {t(d.label)}
          </button>
        ))}
      </div>
      {/* capture opens the camera on phones; on laptops it's a file picker */}
      <input ref={input} type="file" accept="image/*" capture="environment" className="sr-only" onChange={(e) => onFile(e.target.files?.[0])} />
      {status === 'busy' && <p role="status" className="mt-2 text-sm text-teal-800">{t('scanning')}</p>}
      {status === 'ok' && <p role="status" className="mt-2 text-sm text-teal-800">✓ {t('scanned')}</p>}
      {status === 'error' && <p role="alert" className="mt-2 text-sm text-red-700">{t('scanFailed')}</p>}
    </div>
  );
}
