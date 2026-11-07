import { create } from 'zustand';
import type { Strings } from '../i18n/locales/en';
import type { ChatMessage, LangCode, Profile, Session, SuggestedProgram } from '../types';

// PRIVACY: the session lives only in memory. Nothing personal is ever written to storage.
// The only thing cached in localStorage is translated UI text for typed-in languages.

/** What the backend told us about a typed-in language */
export interface CustomLanguage {
  strings: Partial<Strings>;
  dir?: 'ltr' | 'rtl';
  speechLocale?: string;
}

const UI_CACHE_KEY = 'customLanguages.v2';
function loadUiCache(): Record<string, CustomLanguage> {
  try {
    return JSON.parse(localStorage.getItem(UI_CACHE_KEY) ?? '{}');
  } catch {
    return {};
  }
}

const emptySession = (language: LangCode): Session => ({
  language,
  profile: {},
  selected_form: null,
  suggested_programs: [],
  missing_fields: [],
  confirmed: false,
  signature_png: null,
});

interface AppState {
  session: Session;
  /** Onboarding conversation (not part of the shared format) */
  messages: ChatMessage[];
  onboardingDone: boolean;
  /** Low-confidence fields the user has explicitly confirmed in the recap */
  confirmedFields: string[];
  voiceOn: boolean;
  customLanguages: Record<string, CustomLanguage>;

  setLanguage: (lang: LangCode) => void;
  mergeProfile: (fields: Profile) => void;
  setFieldValue: (key: string, value: unknown) => void;
  confirmField: (key: string) => void;
  addMessage: (msg: Omit<ChatMessage, 'id'>) => string;
  setOnboardingDone: (done: boolean) => void;
  selectForm: (formId: string | null) => void;
  setPrograms: (p: SuggestedProgram[]) => void;
  setMissingFields: (f: string[]) => void;
  setSignature: (png: string | null) => void;
  setConfirmed: (c: boolean) => void;
  setVoiceOn: (on: boolean) => void;
  setCustomLanguage: (lang: LangCode, info: CustomLanguage) => void;
  /** Wipe everything personal (start over / after download) */
  reset: () => void;
}

export const useAppStore = create<AppState>((set) => ({
  session: emptySession('en'),
  messages: [],
  onboardingDone: false,
  confirmedFields: [],
  voiceOn: true,
  customLanguages: loadUiCache(),

  setLanguage: (language) => set((s) => ({ session: { ...s.session, language } })),

  // Only overwrite a field when the new value is real; keep the higher-confidence one otherwise
  mergeProfile: (fields) =>
    set((s) => {
      const profile = { ...s.session.profile };
      for (const [k, f] of Object.entries(fields ?? {})) {
        if (!f || typeof f !== 'object') continue;
        const empty = f.value === null || f.value === undefined || f.value === '';
        if (empty && profile[k]?.value != null) continue;
        profile[k] = { value: f.value ?? null, confidence: Number(f.confidence) || 0, source: f.source ?? null };
      }
      return {
        session: { ...s.session, profile },
        // new data for a field means it needs re-confirming if it's low confidence
        confirmedFields: s.confirmedFields.filter((k) => !(k in fields)),
      };
    }),

  // A manual edit on the review screen is the user's own word: full confidence
  setFieldValue: (key, value) =>
    set((s) => ({
      session: {
        ...s.session,
        profile: { ...s.session.profile, [key]: { value, confidence: 1, source: s.session.profile[key]?.source ?? 'gap_voice' } },
      },
      confirmedFields: [...new Set([...s.confirmedFields, key])],
    })),

  confirmField: (key) => set((s) => ({ confirmedFields: [...new Set([...s.confirmedFields, key])] })),

  addMessage: (msg) => {
    const id = crypto.randomUUID();
    set((s) => ({ messages: [...s.messages, { ...msg, id }] }));
    return id;
  },
  setOnboardingDone: (onboardingDone) => set({ onboardingDone }),
  selectForm: (selected_form) =>
    set((s) => ({ session: { ...s.session, selected_form, missing_fields: [], confirmed: false, signature_png: null } })),
  setPrograms: (suggested_programs) => set((s) => ({ session: { ...s.session, suggested_programs } })),
  setMissingFields: (missing_fields) => set((s) => ({ session: { ...s.session, missing_fields } })),
  setSignature: (signature_png) => set((s) => ({ session: { ...s.session, signature_png } })),
  setConfirmed: (confirmed) => set((s) => ({ session: { ...s.session, confirmed } })),
  setVoiceOn: (voiceOn) => set({ voiceOn }),
  setCustomLanguage: (lang, info) =>
    set((s) => {
      const customLanguages = { ...s.customLanguages, [lang.trim().toLowerCase()]: info };
      try {
        localStorage.setItem(UI_CACHE_KEY, JSON.stringify(customLanguages));
      } catch {
        // private mode: keep in memory only
      }
      return { customLanguages };
    }),
  reset: () =>
    set((s) => ({
      session: emptySession(s.session.language),
      messages: [],
      onboardingDone: false,
      confirmedFields: [],
    })),
}));

/** Convenience selector: current language */
export const useLanguageCode = () => useAppStore((s) => s.session.language);
