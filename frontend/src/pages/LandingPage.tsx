import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { isKnownLang, LANGUAGES, useT } from '../i18n/strings';
import { useAppStore } from '../store/profileStore';

export default function LandingPage() {
  const t = useT();
  const navigate = useNavigate();
  const language = useAppStore((s) => s.session.language);
  const { setLanguage, reset } = useAppStore();
  const [otherOpen, setOtherOpen] = useState(!isKnownLang(language));
  const [otherText, setOtherText] = useState(isKnownLang(language) ? '' : language);

  const otherSelected = otherOpen;
  const canStart = !otherSelected || otherText.trim().length > 0;

  function pickPreset(code: (typeof LANGUAGES)[number]['code']) {
    setOtherOpen(false);
    setLanguage(code);
  }

  function pickOther() {
    setOtherOpen(true);
    if (otherText.trim()) setLanguage(otherText.trim());
  }

  function typeOther(value: string) {
    setOtherText(value);
    // Keep UI in English until they've typed something
    setLanguage(value.trim() || 'en');
  }

  function start() {
    if (!canStart) return;
    reset();
    navigate('/onboarding');
  }

  const btn = (active: boolean) =>
    `min-h-16 rounded-xl border-2 px-3 py-2 text-start transition ${
      active ? 'border-teal-600 bg-teal-50' : 'border-stone-200 bg-white hover:border-stone-300'
    }`;

  return (
    <main className="mx-auto max-w-3xl px-4 py-12 sm:py-20">
      <h1 className="text-4xl font-bold leading-tight tracking-tight text-stone-900 sm:text-5xl">{t('tagline')}</h1>
      <p className="mt-4 max-w-xl text-lg text-stone-600">{t('subtitle')}</p>

      <h2 className="mt-12 mb-4 text-sm font-semibold uppercase tracking-wide text-stone-500">{t('chooseLanguage')}</h2>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {LANGUAGES.map((l) => (
          <button
            key={l.code}
            onClick={() => pickPreset(l.code)}
            aria-pressed={!otherSelected && language === l.code}
            className={btn(!otherSelected && language === l.code)}
          >
            <span className="block text-lg font-medium">{l.native}</span>
            <span className="block text-xs text-stone-500">{l.english}</span>
          </button>
        ))}
        <button onClick={pickOther} aria-pressed={otherSelected} aria-expanded={otherSelected} className={btn(otherSelected)}>
          <span className="block text-lg font-medium">{t('otherLanguage')} …</span>
          <span className="block text-xs text-stone-500">Other language</span>
        </button>
      </div>

      {otherSelected && (
        <form
          onSubmit={(e) => { e.preventDefault(); start(); }}
          className="mt-4"
        >
          <label htmlFor="other-lang" className="mb-1.5 block text-sm font-medium text-stone-700">
            {t('otherLanguageHint')}
          </label>
          <input
            id="other-lang"
            value={otherText}
            onChange={(e) => typeOther(e.target.value)}
            placeholder={t('otherLanguagePlaceholder')}
            autoFocus
            dir="auto"
            className="min-h-12 w-full rounded-xl border border-stone-300 bg-white px-4 text-lg outline-none focus:border-teal-600 focus:ring-2 focus:ring-teal-100 sm:max-w-sm"
          />
        </form>
      )}

      <button
        onClick={start}
        disabled={!canStart}
        className="mt-10 w-full rounded-xl bg-teal-700 px-8 py-4 text-lg font-semibold text-white hover:bg-teal-800 disabled:opacity-40 sm:w-auto"
      >
        {t('start')} →
      </button>
      <p className="mt-4 text-sm text-stone-500">{t('trust')}</p>
    </main>
  );
}
