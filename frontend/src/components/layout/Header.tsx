import { Link } from 'react-router-dom';
import { isKnownLang, LANGUAGES, useT } from '../../i18n/strings';
import { useAppStore } from '../../store/profileStore';
import type { LangCode } from '../../types';

export default function Header() {
  const t = useT();
  const language = useAppStore((s) => s.session.language);
  const setLanguage = useAppStore((s) => s.setLanguage);
  const hasInfo = useAppStore((s) => s.onboardingDone);
  return (
    <header className="border-b border-stone-200 bg-white">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
        <Link to={hasInfo ? '/choose' : '/'} className="text-lg font-semibold text-teal-800">
          {t('appName')}
        </Link>
        <select
          aria-label={t('languageLabel')}
          value={language}
          onChange={(e) => setLanguage(e.target.value as LangCode)}
          className="rounded-lg border border-stone-300 bg-white px-3 py-2 text-sm"
        >
          {!isKnownLang(language) && <option value={language}>{language}</option>}
          {LANGUAGES.map((l) => (
            <option key={l.code} value={l.code}>{l.native}</option>
          ))}
        </select>
      </div>
    </header>
  );
}
