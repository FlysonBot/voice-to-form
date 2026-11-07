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
| How is audio sent: multipart upload or base64 in JSON? Which format (webm/wav)? | DRAFT (P2) | Multipart file field `audio`, sent as the browser's `MediaRecorder` records it (`audio/webm;codecs=opus`). Gemini accepted webm directly in P2's test; no conversion needed. Keep clips under a minute. |
| How is speech returned: URL, base64, or text only (browser speaks it)? | DRAFT (P2 finding; P3 decides) | Text only for now: no TTS model is listed for P2's Gemini key, so the browser's `speechSynthesis` speaks the text. |
| Error response shape | DRAFT (P2) | `{"error": "<readable message>", "retryable": true\|false}`. 422 bad input, 400 missing audio, 502 Gemini failed (e.g. rate limit, `retryable: true`), 500 anything else. Messages never echo submitted values. |
| Where the shared profile schema lives, and who writes it | DRAFT (P2) | `gemini/profile_fields.py` (`ONBOARDING_FIELDS`), owned by P2; key list in `gemini/README.md`. **Decided:** names and addresses use separate keys: `first_name`, `middle_name`, `last_name`, `address_street`, `address_unit`, `address_city`, `address_zip` (no `full_name` or `address` key). No state key; P1 writes "CA" into State fields. |
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
- **Request (multipart):** `audio` (file; leave it out on the very first turn, and the reply is a greeting plus the first question), `session` (JSON string, the shared data format). Onboarding also reads two extra session keys the client keeps: `skipped` (list of profile keys the user skipped) and `last_question` (the question just asked).
- **Response (JSON):** `{"transcript", "intent": "answer|skip|correction|unclear|question|off_topic", "profile": <merged profile>, "skipped": [...], "updated_keys": [...], "rejected_keys": [...], "next_question": "<in session.language>", "done": bool, "remaining": [...]}`. The client replaces `session.profile` and `session.skipped` with these, sets `last_question = next_question`, and speaks `next_question`. New values carry `source: "onboarding_voice"`. `done` is computed from the field list, not by Gemini. `rejected_keys` = values that failed validation; those fields stay in `remaining`.
- **Mock:** `?mock=true` returns a mid-onboarding turn (household answered).
- **Notes:** each turn makes two Gemini calls (transcribe, then extract), ~2.5 s total. `transcript` is the plain transcription. Names the user didn't spell out letter by letter come back with confidence 0.7, so the recap asks the user to confirm them.
- **Code:** `gemini/` (`run_onboarding_turn`, route in `gemini/router.py`). Live test `gemini/scripts/live_e2e.py`: a full 16-answer Spanish onboarding plus 5 gap fields, 61/61 checks pass.
- **Open:** route ownership P2 vs P3. Draft: P2 serves it, P3 owns the mic loop and speaking.
- **Status:** DRAFT (P2)

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
- **Request (multipart):** `audio` (file), `session` (JSON string, shared data format; uses `language` and `selected_form`), `field` (JSON string: `{"key", "label_en", "type", "options", "description_en", "sensitive"}`, where `type` is `string|name|digits|date|number|int|phone|zip|email|enum|bool`), `question` (optional, the question the user heard).
- **Response (JSON):** `{"field_key", "transcript", "status": "answered|skipped|leave_blank|unclear", "value": <typed or null>, "confidence", "source": "gap_voice", "clarification_question": "<in session.language, only when unclear>"}`. The client writes `{value, confidence, source}` into `session.profile[field_key]`. `sensitive` fields (SSN, account numbers) are capped at confidence 0.79 so the recap always asks the user to confirm them.
- **Mock:** `?mock=true` returns a parsed SDG&E account number.
- **Code:** `gemini/` (`parse_voice_answer`; answer parsing is P2's scope). P3 can serve the route or call the function from `voice/`. Tested against real Gemini: spoken Spanish account number → correct digits.
- **Status:** DRAFT (P2)

### `POST /recap` (P3 Voice) — consumer: P4
- **Does:** profile + language → recap text (+ audio)
- **Request (JSON):** `{"session": <shared data format>}` (language is `session.language`). Also accepted: `{"language", "profile"}`. Optional: `form_name`, `blank_fields` (e.g. `["citizenship_status"]`, mentioned in the outro), `with_audio`.
- **Response (JSON):** `{"items": [{"field": "first_name", "label": "<in user's language>", "value": "...", "needs_confirm": true|false}], "text": "<full recap in user's language>"}`. `needs_confirm` is true when confidence < 0.8.
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
