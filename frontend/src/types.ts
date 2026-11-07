// ─── Shared data format (CLAUDE.md "Shared data format") + API contract (API.md) ───
// The client keeps the whole session in memory and sends it on every call.

export type KnownLang = 'en' | 'es' | 'vi' | 'tl' | 'zh' | 'ar' | 'fr';
/** A preset code, or a language name the user typed in (e.g. "Korean") */
export type LangCode = KnownLang | (string & {});

export type FieldSource = 'onboarding_voice' | 'id_photo' | 'document' | 'gap_voice';

/** One profile entry. confidence < 0.8 must be confirmed by the user in the recap. */
export interface ProfileField<T = unknown> {
  value: T | null;
  confidence: number;
  source: FieldSource | null;
}

export interface HouseholdMember {
  first_name: string;
  relationship: string;
  date_of_birth: string;
}

/** Keys are owned by the backend schema (full_name, address, household_size, household_members, …). */
export type Profile = Record<string, ProfileField>;

export interface SuggestedProgram {
  name: string;
  /** Why they may qualify, in the user's language. Never a guarantee. */
  why: string;
  /** Official source (.gov, sdge.com, …) */
  source_url: string;
  /** Set when we can fill this program's form */
  form_id?: string | null;
}

export interface Session {
  language: LangCode;
  profile: Profile;
  selected_form: string | null;
  suggested_programs: SuggestedProgram[];
  missing_fields: string[];
  confirmed: boolean;
  /** base64 PNG (no data: prefix) */
  signature_png: string | null;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  text: string;
}

// ─── Endpoint responses ─────────────────────────────────────────────────────

/** Optional speech from Gemini TTS. If absent, the browser speaks the text. */
export interface SpokenText {
  audio_b64?: string | null;
  audio_mime?: string | null;
}

/** POST /onboarding/turn  (request is multipart: audio?, text?, session, history) */
export interface OnboardingTurnResponse extends SpokenText {
  /** Next question / reply, in the user's language */
  reply: string;
  /** What Gemini heard, shown as the user's chat bubble */
  transcript?: string | null;
  /** Fields extracted from this answer. A full `profile` is also accepted. */
  profile_updates?: Profile;
  profile?: Profile;
  done: boolean;
  /** Keys Gemini heard but the backend's validation threw out (e.g. an 11-digit phone).
   *  The backend's `reply` may still say "thank you", so the frontend re-asks these. */
  rejected_keys?: string[];
}

/** POST /profile/extract */
export interface ExtractResponse {
  fields: Profile;
}

/** POST /programs/find */
export interface ProgramsResponse {
  suggested_programs: SuggestedProgram[];
}

/** POST /form/gaps */
export interface GapsResponse {
  missing_fields: string[];
}

/** POST /voice/question */
export interface QuestionResponse extends SpokenText {
  text: string;
}

/** POST /voice/answer  (request is multipart: audio?, text?, field, session) */
export interface AnswerResponse {
  value: unknown;
  confidence: number;
  transcript?: string | null;
  /** P2: answered | skipped | leave_blank | unclear */
  status?: string;
  /** Set when status is "unclear": ask this instead of accepting the value */
  clarification_question?: string | null;
}

/** POST /recap */
export interface RecapItem {
  field: string;
  label: string;
  value: unknown;
  needs_confirm: boolean;
}
export interface RecapResponse extends SpokenText {
  items: RecapItem[];
  text: string;
}

/** POST /translate-ui (P4 proposal, optional): only for languages typed into "Other" */
export interface TranslateUiResponse {
  strings: Record<string, string>;
  dir?: 'ltr' | 'rtl';
  speechLocale?: string;
}
