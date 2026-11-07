import { useAppStore } from '../store/profileStore';
import type { KnownLang, LangCode } from '../types';
import { toBcp47 } from './speechLang';
import { ar } from './locales/ar';
import { en, type Key, type Strings } from './locales/en';
import { es } from './locales/es';
import { fr } from './locales/fr';
import { tl } from './locales/tl';
import { vi } from './locales/vi';
import { zh } from './locales/zh';

export type { Key, Strings };
export { en as EN_STRINGS };

export const LANGUAGES: { code: KnownLang; native: string; english: string; rtl?: boolean }[] = [
  { code: 'en', native: 'English', english: 'English' },
  { code: 'es', native: 'Español', english: 'Spanish' },
  { code: 'vi', native: 'Tiếng Việt', english: 'Vietnamese' },
  { code: 'tl', native: 'Tagalog', english: 'Tagalog' },
  { code: 'zh', native: '中文', english: 'Mandarin' },
  { code: 'ar', native: 'العربية', english: 'Arabic', rtl: true },
  { code: 'fr', native: 'Français', english: 'French' },
];

const PRESET: Record<KnownLang, Partial<Strings>> = { en, es, vi, tl, zh, ar, fr };

export const isKnownLang = (lang: LangCode): lang is KnownLang => lang in PRESET;

// Right-to-left for presets flagged rtl, and for typed-in names of RTL languages
export function isRtl(lang: LangCode) {
  const preset = LANGUAGES.find((l) => l.code === lang);
  if (preset) return !!preset.rtl;
  return /arab|عرب|hebrew|עברית|farsi|persian|فارسی|dari|urdu|اردو|pashto|پښتو|kurd|sorani|yiddish|uyghur|sindhi/i.test(lang);
}

/**
 * UI text in the current language. Presets are bundled; typed-in languages use
 * translations fetched from the backend (see useUiTranslation), falling back to English.
 */
export function useT() {
  const lang = useAppStore((s) => s.session.language);
  const custom = useAppStore((s) => s.customLanguages[s.session.language.trim().toLowerCase()]);
  const table: Partial<Strings> = isKnownLang(lang) ? PRESET[lang] : (custom?.strings ?? {});
  return (key: Key) => table[key] || en[key];
}

/** Name to put in a Gemini prompt: "Spanish" for presets, or exactly what the user typed. */
export function languageName(lang: LangCode): string {
  return LANGUAGES.find((l) => l.code === lang)?.english ?? lang.trim();
}

/**
 * Everything the app needs to know about the current language. For typed-in languages,
 * the backend's answer (direction, speech locale) wins over our built-in guesses.
 */
export function useLanguage() {
  const language = useAppStore((s) => s.session.language);
  const custom = useAppStore((s) => s.customLanguages[s.session.language.trim().toLowerCase()]);
  return {
    language,
    name: languageName(language),
    rtl: custom?.dir ? custom.dir === 'rtl' : isRtl(language),
    speechLocale: toBcp47(language) ?? custom?.speechLocale,
    /** True when a typed-in language has been translated by the backend */
    translated: !!custom,
  };
}
