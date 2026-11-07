# frontend

**Owner:** P4 Frontend + demo

**Scope (from CLAUDE.md):** All screens, accessible UI, signature pad, fake demo documents, the pitch and a backup demo video.

React + TypeScript + Vite + Tailwind + Zustand + React Router. There are no other runtime dependencies: the signature pad is a plain canvas, and voice uses browser APIs.

## Run
```bash
cd frontend
npm install
cp .env.example .env   # choose the API mode (see below)
npm run dev            # http://localhost:5173
```
Other commands: `npm run build` (type check + production build to `dist/`), `npm run lint` (oxlint).

`VITE_API_MODE` in `.env`:
| Mode | What it does | Needs backend? |
|---|---|---|
| `local` (default) | In-browser mock with **fake data** (`src/api/mock.ts`) | No |
| `server` | Calls the FastAPI app with `?mock=true` on every endpoint | Yes |
| `live` | FastAPI + Gemini | Yes |

The browser calls `/api/<endpoint>`, and Vite forwards it to `http://localhost:8000/<endpoint>`, with the `/api` prefix stripped (see `vite.config.ts`). The FastAPI app therefore serves the routes exactly as written in API.md, and **needs no CORS setup** during development. Restart `npm run dev` after changing `.env` or `vite.config.ts`.

## Screens (CLAUDE.md user flow)
| Route | Screen | Endpoints used |
|---|---|---|
| `/` | Language picker: 7 big buttons plus "Other" (typed) | — |
| `/onboarding` | Voice onboarding, plus "skip questions with a photo" (ID / pay stub / bill), plus a live profile sidebar (yellow = confidence < 0.8) | `/onboarding/turn`, `/profile/extract` |
| `/choose` | **A** supported-form list · **B** "Find forms I qualify for" · immigration-form notice | — |
| `/programs` | Path B results: "you *may* qualify", with the official source link | `/programs/find` |
| `/form/:formId/questions` | Voice gap questions, one at a time, with "Leave it blank" | `/form/gaps`, `/voice/question`, `/voice/answer` |
| `/form/:formId/review` | Recap read aloud. Yellow fields must be confirmed before signing. Fix by typing or 🎤 | `/recap`, `/voice/answer` |
| `/form/:formId/sign` | Finger / mouse signature pad | `/form/fill` |
| `/form/:formId/done` | PDF preview + download, "We don't store your information", Start over | — |

The mic is on every voice screen (onboarding, questions, review). Typing is only a small "Type instead" fallback.

## API contract as the frontend implements it
Types: `src/types.ts`. Calls: `src/api/client.ts` (one function per endpoint).

The **whole `session`** (CLAUDE.md "Shared data format") is sent on every call. It lives only in memory: nothing personal goes to `localStorage`, URLs or console logs.

| Endpoint | Request | Response the frontend reads |
|---|---|---|
| `POST /onboarding/turn` | **multipart**: `audio` (file, optional), `text` (optional), `session` (JSON string), `history` (JSON string `[{role,text}]`) | `{ reply, done, profile_updates? \| profile?, transcript?, audio_b64?, audio_mime? }` |
| `POST /profile/extract` | multipart: `image`, `doc_type` (`id`\|`pay_stub`\|`bill`), `session` | `{ fields: { key: {value, confidence, source} } }` (merged into the profile) |
| `POST /programs/find` | JSON `{ session }` | `{ suggested_programs: [{name, why, source_url, form_id}] }` |
| `POST /form/gaps` | JSON `{ session, form_id }` | `{ missing_fields: [...] }` |
| `POST /voice/question` | JSON `{ session, field, language }` | `{ text, audio_b64?, audio_mime? }` |
| `POST /voice/answer` | **multipart**: `audio`, `text`, `field`, `session` | `{ value, confidence, transcript? }` |
| `POST /recap` | JSON `{ session }` | `{ items: [{field, label, value, needs_confirm}], text, audio_b64? }` |
| `POST /form/fill` | JSON `{ session, form_id, signature_png }` (base64 PNG, no `data:` prefix) | PDF bytes (`application/pdf`) |
| `POST /translate-ui` *(optional, P4 proposal)* | JSON `{ language, strings }` | `{ strings, dir?, speechLocale? }`. Only used for languages typed into "Other". If it's missing, the UI stays in English. |

### P4 proposals for the open questions in API.md
- **Audio in:** multipart file `audio` from the browser's `MediaRecorder`. That's usually `audio/webm`; Safari gives `audio/mp4`. The `text` field carries the browser's **own live transcript** (Chrome, Edge, Safari) or typed text as a backup, so the backend can transcribe `audio` with Gemini or fall back to `text`. The first `/onboarding/turn` has neither, which means: greet the user and ask the first question.
- **Speech out:** optional `audio_b64` + `audio_mime` on `/onboarding/turn`, `/voice/question` and `/recap`. The frontend plays the clip; if it's missing or fails, the browser's `speechSynthesis` reads `reply` / `text`. The text types out on screen in sync either way.
- **Errors:** any non-2xx is shown as a friendly "try again" message and never breaks the flow, so any error body shape works. The first 200 characters are kept for debugging.
- **`/onboarding/turn` result:** send either `profile_updates` (only the fields changed this turn) or the full `profile`. The frontend merges them, and an empty value never overwrites a known one.
- **"Leave it blank":** stored as `{ value: "", confidence: 1, source: "gap_voice" }`. The recap shows "Left blank — fill in by hand". `/form/fill` should leave those PDF fields empty.

## Integration checklist (when merging with the backend)
1. **Entry file:** run the FastAPI app on port 8000 with the routes at the root paths in API.md. If it runs elsewhere, change `target` in `vite.config.ts`.
2. **Test with backend mocks first:** set `VITE_API_MODE=server`, restart, and walk the whole flow. Then switch to `live`.
3. **Profile keys:** the frontend shows **any** key the backend sends. Labels for known keys (`full_name`, `address`, `household_size`, `household_members`, `monthly_income`, `sdge_account_number`, …) are in `src/fields.ts` → `FIELD_LABELS`, translated in `src/i18n/locales/*.ts` as `f_<key>`. When P2 finalizes the schema, add new keys in both places. Unknown keys still display, just with a humanized English label.
4. **Form ids:** `src/forms.ts` lists the forms. `sdge_care` is `ready: true`; the others say "Coming soon". The ids must match P1's `form_engine` ids. Flip `ready` when P1 supports another form.
5. **Program results:** a `suggested_programs[].form_id` that matches a ready form gets a "Fill out this form" button. Anything else just shows the official link.
6. **`household_members`:** displayed as "Ana (daughter), Luis (son)". It's not editable by typing; users fix it by voice (🎤 on the review screen).
7. **Serving in production (optional):** `npm run build`, then serve `frontend/dist/` with FastAPI `StaticFiles` and mount the API under `/api`. The frontend already calls `/api/...`. Not needed for the demo, where `npm run dev` is enough.

## Layout
```
src/
  api/client.ts       one function per endpoint + VITE_API_MODE switch
  api/mock.ts         local mock, FAKE DATA ONLY (Maria Lopez, fake ID / pay stub)
  types.ts            shared session format + endpoint response types
  fields.ts           profile labels, value formatting, confidence threshold (0.8)
  forms.ts            supported forms
  store/profileStore.ts  session in memory (Zustand); reset() wipes it
  hooks/useListener.ts   mic: records audio + live transcript; 3.5 s of silence = done
  hooks/useReplyPlayer.ts plays Gemini audio or browser voice; text types out in sync
  hooks/useSpeaker.ts    browser speechSynthesis + voice picking
  i18n/               UI text: en, es, vi complete; tl, zh, ar, fr partial (fall back to en)
  pages/              one file per screen (see the table above)
  components/         chat, voice (DocScan, VoiceToggle), sign (SignaturePad), layout
```

## Demo notes
- Demo language: **Spanish**. Arabic flips the layout right-to-left.
- Use **Chrome**. Mic transcription in the browser works in Chrome, Edge and Safari; in Firefox the mic records but there's no live transcript, so tap to stop.
- In `local` mode the PDF is a plain placeholder listing the values. The real CARE PDF comes from P1's `/form/fill` in `server` / `live` mode.
- The first use of the mic asks for browser permission. Allow it **before** the demo.

## Privacy
Session in memory only, and Start over wipes it. No personal data in `localStorage`, URLs or logs; the only thing cached is translated UI text for typed-in languages. Fake data only in the mock and the demo.
