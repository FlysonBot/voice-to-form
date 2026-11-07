import { useEffect, useState } from 'react';
import { translateUi } from '../api/client';
import { useAppStore } from '../store/profileStore';
import { EN_STRINGS, isKnownLang, type Key, type Strings } from './strings';

const DEBOUNCE_MS = 900; // the language name is typed letter by letter on the landing page

/**
 * For typed-in languages, asks the backend (Gemini) to translate the whole UI once and
 * tell us the text direction and speech locale. Cached in memory and localStorage.
 * Returns true while translating.
 */
export function useUiTranslation() {
  const language = useAppStore((s) => s.session.language);
  const cached = useAppStore((s) => !!s.customLanguages[s.session.language.trim().toLowerCase()]);
  const setCustomLanguage = useAppStore((s) => s.setCustomLanguage);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    if (isKnownLang(language) || cached || language.trim().length < 2) return;
    let cancelled = false;
    const timer = window.setTimeout(async () => {
      setPending(true);
      try {
        const result = await translateUi(language, EN_STRINGS);
        if (cancelled || !result?.strings) return;
        // Keep only known, non-empty string keys; anything missing falls back to English
        const strings: Partial<Strings> = {};
        for (const k of Object.keys(EN_STRINGS) as Key[]) {
          const v = result.strings[k];
          if (typeof v === 'string' && v.trim()) strings[k] = v;
        }
        setCustomLanguage(language, {
          strings,
          dir: result.dir === 'rtl' || result.dir === 'ltr' ? result.dir : undefined,
          speechLocale: typeof result.speechLocale === 'string' && result.speechLocale.trim() ? result.speechLocale.trim() : undefined,
        });
      } catch {
        // Stay in English if translation fails
      } finally {
        if (!cancelled) setPending(false);
      }
    }, DEBOUNCE_MS);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
      setPending(false);
    };
  }, [language, cached, setCustomLanguage]);

  return pending;
}
