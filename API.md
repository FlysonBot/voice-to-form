# API contract (skeleton, nothing here is decided yet)

Each owner fills in **their own** endpoints. The consumer (mostly P4 frontend) comments if something doesn't work for them. Status: `TBD` = not decided, `DRAFT` = owner proposed, `AGREED` = owner and consumers OK'd.

## Rules already in CLAUDE.md
- The client sends the **whole profile** on every call. The server keeps nothing (session memory only, no database).
- Profile shape: see "Shared data format" in `CLAUDE.md`. Fields under 0.8 confidence need user confirmation.
- Every endpoint supports `?mock=true`, returning sample JSON.
- Gemini failures return a clear error and never crash the flow.
- All user-facing text is in `language`; values written to the PDF are English/Latin characters.

## Open across all endpoints (owners decide, then record here)
| Question | Status | Decision |
|---|---|---|
| How is audio sent: multipart upload or base64 in JSON? Which format (webm/wav)? | TBD | |
| How is speech returned: URL, base64, or text only (browser speaks it)? | TBD, depends on whether Gemini TTS works (P3 test) | |
| Error response shape | TBD | |
| Where the shared profile schema lives, and who writes it | TBD | |
| Where the entry file that wires all routers together lives | TBD | |

## Endpoints

### `POST /form/fill` (P1 Form engine) — consumer: P4
- **Does:** profile + signature → filled PDF
- **Request (JSON):** `{"session": <shared data format>, "form_id": "sdge_care", "signature_png": "<base64 PNG>"}`. `signature_png` may be null (draft preview).
- **Response:** `200`, `Content-Type: application/pdf`, the filled PDF bytes. Errors use the shared error shape.
- **Mock:** `?mock=true` fills from a built-in fake profile.
- **Status:** DRAFT (default proposed, P4 to confirm base64 signature + file download)

### `POST /onboarding/turn` (P2 Gemini + P3 Voice) — consumer: P4
- **Does:** user's audio + current profile → updated profile + next spoken question (or `done: true`)
- **Request / Response:** TBD
- **Open:** who owns the endpoint, P2 (extraction logic) or P3 (conversation)? Audio and speech format (see above).
- **Status:** TBD

### `POST /profile/extract` (P2 Gemini) — consumer: P4
- **Does:** photo of a document → profile fields with confidence
- **Request (multipart):** `image` (jpg/png file), `doc_type` (`id` | `pay_stub` | `bill`), `session` (JSON string, the current profile)
- **Response (JSON):** `{"fields": {"<profile_key>": {"value": ..., "confidence": 0.0-1.0, "source": "id_photo" | "document"}}}`. Only fields it actually read; the client merges them into the profile.
- **Mock:** `?mock=true` returns sample fields.
- **Status:** DRAFT (P2 to confirm)

### `POST /programs/find` (P2 Gemini) — consumer: P4 (Path B, cut by default)
- **Does:** profile → `suggested_programs`
- **Request (JSON):** `{"session": <shared data format>}`
- **Response (JSON):** `{"suggested_programs": [{"name", "why", "source_url", "form_id"}]}`. `why` in the user's language; `source_url` must be an official source. Never states eligibility as certain.
- **Mock:** `?mock=true` returns a list containing SDG&E CARE.
- **Status:** DRAFT (P2 to confirm; cut by default)

### `POST /form/gaps` (P2 Gemini) — needs P1's field list
- **Does:** profile + form → `missing_fields` (form-specific only)
- **Request (JSON):** `{"session": <shared data format>, "form_id": "sdge_care"}`
- **Response (JSON):** `{"missing_fields": ["sdge_account_number", ...]}`. Only fields the form needs that the profile lacks. Low-confidence fields are not this endpoint's job; the recap flags those.
- **Mock:** `?mock=true` returns `["sdge_account_number"]`.
- **Open:** how P1 hands over the list of fields a form needs (e.g. a JSON file in `form_engine/`).
- **Status:** DRAFT (P2 to confirm)

### `POST /voice/question` (P3 Voice) — consumer: P4
- **Does:** missing field + language → question text (+ audio)
- **Request / Response:** TBD
- **Status:** TBD

### `POST /voice/answer` (P3 Voice) — consumer: P4
- **Does:** audio + field → parsed value
- **Request / Response:** TBD
- **Status:** TBD

### `POST /recap` (P3 Voice) — consumer: P4
- **Does:** profile + language → recap text (+ audio)
- **Request (JSON):** `{"session": <shared data format>}` (language is `session.language`)
- **Response (JSON):** `{"items": [{"field": "full_name", "label": "<in user's language>", "value": "...", "needs_confirm": true|false}], "text": "<full recap in user's language>"}`. `needs_confirm` is true when confidence < 0.8.
- **Audio:** TBD, depends on the TTS test (see top). Until then the browser speaks `text`.
- **Mock:** `?mock=true` returns sample items.
- **Status:** DRAFT for the JSON part (P3 to confirm); audio TBD
