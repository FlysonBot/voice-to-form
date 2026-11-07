import { formatValue, isFilled, labelFor, needsConfirm, ONBOARDING_KEYS } from '../../fields';
import { useT, type Key } from '../../i18n/strings';
import type { FieldSource, Profile } from '../../types';

const SOURCE: Record<FieldSource, { icon: string; label: Key }> = {
  onboarding_voice: { icon: '🎤', label: 'srcVoice' },
  gap_voice: { icon: '🎤', label: 'srcVoice' },
  id_photo: { icon: '🪪', label: 'srcPhoto' },
  document: { icon: '📄', label: 'srcDocument' },
};

/** Live view of the profile as it fills in. Low-confidence values are yellow. */
export default function ProfileSidebar({ profile }: { profile: Profile }) {
  const t = useT();
  // Core onboarding fields first, then anything else the backend added
  const keys = [...ONBOARDING_KEYS, ...Object.keys(profile).filter((k) => !ONBOARDING_KEYS.includes(k) && isFilled(profile, k))];
  return (
    <aside className="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-stone-200">
      <h2 className="mb-1 text-sm font-semibold uppercase tracking-wide text-stone-500">{t('yourInfo')}</h2>
      <p className="mb-3 text-xs text-stone-400">🔒 {t('noStore')}</p>
      <ul className="space-y-1.5">
        {keys.map((key) => {
          const filled = isFilled(profile, key);
          const yellow = needsConfirm(profile, key);
          const src = profile[key]?.source;
          return (
            <li key={key} className={`flex items-start gap-2.5 rounded-lg px-2 py-1.5 text-sm ${yellow ? 'bg-amber-50 ring-1 ring-amber-300' : ''}`}>
              <span
                className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-xs transition-colors ${
                  filled ? (yellow ? 'bg-amber-400 text-white' : 'bg-teal-600 text-white') : 'bg-stone-200 text-transparent'
                }`}
                aria-hidden
              >
                {yellow ? '?' : '✓'}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block text-stone-500">{labelFor(key, t)}</span>
                {filled && (
                  <span className="block break-words font-medium text-stone-900">
                    {formatValue(profile[key]?.value)}
                    {src && SOURCE[src] && (
                      <span className="ms-1.5" title={t(SOURCE[src].label)} aria-label={t(SOURCE[src].label)}>
                        {SOURCE[src].icon}
                      </span>
                    )}
                  </span>
                )}
                {yellow && <span className="block text-xs font-medium text-amber-800">{t('needsCheck')}</span>}
              </span>
            </li>
          );
        })}
      </ul>
    </aside>
  );
}
