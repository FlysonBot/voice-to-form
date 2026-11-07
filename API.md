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
| How is audio sent: multipart upload or base64 in JSON? Which format (webm/wav)? | DRAFT (P3) | Base64 in JSON: `audio_b64` + `mime_type`. The browser recorder converts to 16 kHz mono WAV (`audio/wav`). |
| How is speech returned: URL, base64, or text only (browser speaks it)? | DRAFT (P3) | Text in every response. The frontend calls `POST /voice/tts` → base64 WAV; on error or >7 s it falls back to browser `speechSynthesis` (`frontend/src/voice/speaker.js`). |
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
- **Request (JSON):** `{"language": "es" | "auto", "profile": {...}, "audio_b64": "<base64 WAV>" | null, "mime_type": "audio/wav", "last_question": "<what we last said>", "user_text": "skip" | null}`. First turn: no audio → greeting + first question.
- **Response (JSON):** `{"profile": {...updated}, "transcript": "...", "say": "<next question, user's language>", "done": false, "remaining_fields": ["phone", ...], "updated_fields": ["first_name", ...], "language": "es", "language_changed": false}`
- **Language auto-detect:** `language` in the response is the language the user actually speaks (detected each turn). When `language_changed` is true, P4 should store it in `session.language` and use it for all later calls.
- **Profile keys:** `voice/fields.py` (split name/address parts; `full_name` and `address` are derived). Skipped optional fields carry `"skipped": true`.
- **Mock:** `?mock=true` plays a scripted Spanish conversation (fake Maria Lopez), one step per call.
- **Open:** P3 has a working version in `voice/onboarding.py`; P2 can take over the prompt/schema there.
- **Status:** DRAFT (P3)

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
- **Request (JSON):** `{"language": "es", "field": "sdge_account_number", "description": "SDG&E account number from the bill", "form_name": "SDG&E CARE", "retry_reason": "", "with_audio": false}`
- **Response (JSON):** `{"field": "...", "question": "<user's language>"}` (+ `audio_b64`, `audio_mime_type` if `with_audio`; null if TTS failed)
- **Refuses** immigration/citizenship fields with `400`.
- **Mock:** `?mock=true`
- **Status:** DRAFT (P3)

### `POST /voice/answer` (P3 Voice) — consumer: P4
- **Does:** audio + field → parsed value
- **Request (JSON):** `{"language": "es", "field": "...", "description": "...", "question": "<what we asked>", "audio_b64": "...", "mime_type": "audio/wav"}`
- **Response (JSON):** `{"transcript", "intent": "answer|skip|leave_blank|repeat|unclear|wrong", "value", "confidence", "reply": "<user's language>", "profile_entry": {"value", "confidence", "source": "gap_voice"} | null}`
- **Mock:** `?mock=true`
- **Status:** DRAFT (P3)

### `POST /recap` (P3 Voice) — consumer: P4
- **Does:** profile + language → recap text (+ audio)
- **Request (JSON):** `{"session": <shared data format>}` (language is `session.language`). Also accepted: `{"language", "profile"}`. Optional: `form_name`, `blank_fields` (e.g. `["citizenship_status"]`, mentioned in the outro), `with_audio`.
- **Response (JSON):** `{"items": [{"field": "full_name", "label": "<in user's language>", "value": "...", "needs_confirm": true|false}], "text": "<full recap in user's language>"}`. `needs_confirm` is true when confidence < 0.8.
- **Audio:** TBD, depends on the TTS test (see top). Until then the browser speaks `text`.
- **Mock:** `?mock=true` returns sample items.
- **Also returns:** `intro`, `outro`, `script` (= `text`), `needs_confirmation` (list of field keys), and per item `spoken` and `low_confidence` (= `needs_confirm`).
- **Status:** DRAFT (P3 implemented this shape); audio via `/voice/tts` or `with_audio`

### `POST /recap/correct` (P3 Voice) — consumer: P4
- **Does:** spoken correction during the recap → which field + new value (or "confirm all")
- **Request (JSON):** `{"language", "profile", "audio_b64", "mime_type", "current_field": ""}`
- **Response (JSON):** `{"transcript", "action": "confirm_all|confirm_field|correct|repeat|unclear", "field", "new_value", "confidence", "reply", "profile": {...updated}}`
- **Status:** DRAFT (P3)

### `POST /voice/tts` (P3 Voice) — consumer: P4
- **Does:** text → speech
- **Request (JSON):** `{"text": "...", "language": "es"}`
- **Response (JSON):** `{"audio_b64": "<base64 WAV>", "mime_type": "audio/wav"}`. Mock returns nulls so the browser voice is used.
- **Status:** DRAFT (P3)
