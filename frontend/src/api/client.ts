// One function per endpoint in API.md. Every call sends the whole session (server keeps nothing).
//
// VITE_API_MODE (in .env):
//   local  – in-browser mock (src/api/mock.ts), no backend needed  ← default
//   server – real backend, every call with ?mock=true (backend sample JSON)
//   live   – real backend + Gemini
// Requests go to /api/<endpoint>; Vite forwards them to the FastAPI app (vite.config.ts).
import type { Strings } from '../i18n/locales/en';
import type {
  AnswerResponse,
  ChatMessage,
  ExtractResponse,
  GapsResponse,
  OnboardingTurnResponse,
  ProgramsResponse,
  QuestionResponse,
  RecapResponse,
  Session,
  TranslateUiResponse,
} from '../types';
import * as mock from './mock';

export type ApiMode = 'local' | 'server' | 'live';
export const API_MODE: ApiMode = (['local', 'server', 'live'] as const).find((m) => m === import.meta.env.VITE_API_MODE) ?? 'local';
const TIMEOUT_MS = 60_000; // Gemini + grounding can be slow

export class ApiError extends Error {}

async function call(path: string, init: RequestInit): Promise<Response> {
  const url = `/api${path}${API_MODE === 'server' ? '?mock=true' : ''}`;
  const ctrl = new AbortController();
  const timer = window.setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  try {
    const res = await fetch(url, { ...init, signal: ctrl.signal });
    if (!res.ok) {
      // Shared error shape is still TBD in API.md; show whatever the server says
      const detail = await res.text().catch(() => '');
      throw new ApiError(`${path} ${res.status}: ${detail.slice(0, 200)}`);
    }
    return res;
  } finally {
    window.clearTimeout(timer);
  }
}

const json = async <T>(path: string, body: unknown): Promise<T> =>
  (await call(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })).json();

const multipart = async <T>(path: string, parts: Record<string, string | Blob | null | undefined>): Promise<T> => {
  const form = new FormData();
  for (const [k, v] of Object.entries(parts)) {
    if (v === null || v === undefined) continue;
    if (v instanceof Blob) form.append(k, v, k === 'audio' ? `answer.${audioExt(v.type)}` : 'upload');
    else form.append(k, v);
  }
  return (await call(path, { method: 'POST', body: form })).json();
};

const audioExt = (mime: string) => (mime.includes('wav') ? 'wav' : mime.includes('mp4') ? 'm4a' : mime.includes('ogg') ? 'ogg' : 'webm');
const history = (messages: ChatMessage[]) => JSON.stringify(messages.map(({ role, text }) => ({ role, text })));

/**
 * One onboarding turn. Sends the recorded audio (Gemini transcribes it) plus the browser's
 * own transcript or typed text as a backup. Empty audio + empty text = first turn (greeting).
 */
export function onboardingTurn(session: Session, messages: ChatMessage[], audio: Blob | null, text: string | null) {
  if (API_MODE === 'local') return mock.onboardingTurn(session, messages, text);
  return multipart<OnboardingTurnResponse>('/onboarding/turn', {
    audio, text, session: JSON.stringify(session), history: history(messages),
  });
}

export function extractFromPhoto(session: Session, image: File, docType: 'id' | 'pay_stub' | 'bill') {
  if (API_MODE === 'local') return mock.extract(docType);
  return multipart<ExtractResponse>('/profile/extract', { image, doc_type: docType, session: JSON.stringify(session) });
}

export function findPrograms(session: Session) {
  if (API_MODE === 'local') return mock.findPrograms(session);
  return json<ProgramsResponse>('/programs/find', { session });
}

export function formGaps(session: Session, formId: string) {
  if (API_MODE === 'local') return mock.formGaps(session, formId);
  return json<GapsResponse>('/form/gaps', { session, form_id: formId });
}

export function voiceQuestion(session: Session, field: string) {
  if (API_MODE === 'local') return mock.voiceQuestion(session, field);
  return json<QuestionResponse>('/voice/question', { session, field, language: session.language });
}

export function voiceAnswer(session: Session, field: string, audio: Blob | null, text: string | null) {
  if (API_MODE === 'local') return mock.voiceAnswer(field, text);
  return multipart<AnswerResponse>('/voice/answer', { audio, text, field, session: JSON.stringify(session) });
}

export function recap(session: Session) {
  if (API_MODE === 'local') return mock.recap(session);
  return json<RecapResponse>('/recap', { session });
}

/** Returns the filled PDF. signature_png is base64 without the data: prefix. */
export async function fillForm(session: Session, formId: string): Promise<Blob> {
  if (API_MODE === 'local') return mock.fillForm(session, formId);
  const res = await call('/form/fill', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session, form_id: formId, signature_png: session.signature_png }),
  });
  return res.blob();
}

/** P4 proposal (optional endpoint): translate the UI for a typed-in language. null = stay in English. */
export async function translateUi(language: string, strings: Strings): Promise<TranslateUiResponse | null> {
  if (API_MODE === 'local') return null;
  try {
    return await json<TranslateUiResponse>('/translate-ui', { language, strings });
  } catch {
    return null;
  }
}
