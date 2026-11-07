# voice

**Owner:** P3 Voice & language

**Scope (from CLAUDE.md):** Mic recording, the voice onboarding conversation, /voice/question, /voice/answer, /recap, TTS plus the browser fallback, re-asking on "that's wrong".

## Files
```
voice/                     (Python package, import as `voice`)
  router.py        FastAPI routes (all support ?mock=true)
  dev_app.py       standalone FastAPI app with just the voice routes (+ CORS)
  onboarding.py    /onboarding/turn — audio + profile -> updated profile + next spoken question
  gaps_recap.py    /voice/question, /voice/answer, /recap, /recap/correct
  tts.py           /voice/tts — Gemini TTS -> WAV (base64)
  fields.py        onboarding field keys + types  <-- agree these keys with Person 1 & 2
  mocks.py         fake Spanish demo data
  gemini_client.py shared client, structured-output helper
  smoke_test.py    real-Gemini test, no mic needed (Gemini TTS speaks fake answers)
frontend/src/voice/        (React components, used by P4's Vite app)
  recorder.js      mic -> 16 kHz WAV, auto-stops after ~1.6 s of silence
  speaker.js       Gemini TTS, falls back to browser speechSynthesis (7 s timeout / errors)
  useVoice.js      hook: say(), listen(), status, mic level
  MicButton.jsx    big mic (tap = talk / done / interrupt)
  VoiceOnboarding.jsx  the voice conversation (Repeat / Skip / Scan buttons)
  GapQuestions.jsx     form-specific gaps; handles skip, "leave it blank", repeat, unclear, "that's wrong"
  VoiceRecap.jsx       read-back, yellow low-confidence fields, voice or tap-to-edit corrections
  VoiceDemo.jsx        standalone page running the whole voice flow
  api.js, i18n.js, voice.css
```
The React files live under `frontend/src/voice/` (not here) because Vite resolves `react` from `frontend/node_modules`; files outside `frontend/` can't import it.

## Run
```bash
# .env at the repo root (copy .env.example)
GEMINI_API_KEY=...
GEMINI_MODEL=<current Flash model from AI Studio>
GEMINI_TTS_MODEL=<current Flash TTS model from AI Studio>
GEMINI_TTS_VOICE=Kore          # optional

# from the repo root (deps are already in pyproject.toml)
uv run uvicorn voice.dev_app:app --reload --port 8000
uv run python -m voice.smoke_test     # real Gemini check, needs the .env above

# frontend/.env
VITE_API_URL=http://localhost:8000
VITE_MOCK=true                 # no key needed; set false for real Gemini
VITE_USE_GEMINI_TTS=true       # set false on demo day if TTS is slow -> browser voice
```
`uv run fastapi dev ...` does not work yet: it needs `fastapi[standard]`, and the repo has plain `fastapi`. Use `uvicorn` as above.

Temporarily render `<VoiceDemo />` in `App.jsx` to try the whole flow. To add the routes to the shared app: `from voice.router import router as voice_router; app.include_router(voice_router)`.

## Endpoints (JSON in, JSON out; audio is base64 WAV)
| Route | Body | Returns |
|---|---|---|
| `POST /onboarding/turn` | `language, profile, audio_b64?, last_question, user_text?` | `profile, transcript, say, done, remaining_fields, updated_fields` |
| `POST /voice/question` | `language, field, description, form_name, retry_reason?` | `question` |
| `POST /voice/answer` | `language, field, description, question, audio_b64` | `transcript, intent, value, confidence, reply, profile_entry` |
| `POST /recap` | `language, profile, form_name, blank_fields` | `intro, items[{field,label,value,low_confidence,spoken}], outro, script, needs_confirmation` |
| `POST /recap/correct` | `language, profile, audio_b64, current_field?` | `action, field, new_value, reply, profile` |
| `POST /voice/tts` | `text, language` | `audio_b64, mime_type` |

`intent` is one of `answer | skip | leave_blank | repeat | unclear | wrong`.

## Alignment with CLAUDE.md
- **Profile entries** are `{value, confidence, source}` with `source` in `onboarding_voice | gap_voice` (corrections count as `gap_voice`). Any field under 0.8 shows yellow and must be confirmed in the recap.
- **`household_members`** is a plain list in the profile, as CLAUDE.md says: `profile.household_members = [{first_name, relationship, date_of_birth}]`. It's `[]` if they live alone (`household_size` = 1).
- **`full_name` and `address`** (the keys in the CLAUDE.md example) are built from the split fields (`first_name / middle_name / last_name`, `address_street / address_unit / address_city / address_zip`), because forms ask for the parts separately. They're never asked or read back. **Person 1:** use whichever keys the CARE PDF needs, and call `voice.fields.add_derived(profile)` right before `/form/fill` so edits made on the review screen carry through.
- **Current benefits** are yes/no per program (`benefits_calfresh`, `benefits_medi_cal`, `benefits_wic`, `benefits_ssi`, `benefits_school_meals`, plus optional `benefits_other`), so they map to form checkboxes.
- **"(+ audio)"** on `/voice/question` and `/recap`: pass `"with_audio": true` to get `audio_b64` back. If TTS fails, `audio_b64` is `null` and the text still comes back. The frontend components use `/voice/tts` instead, so they can fall back to the browser voice after 7 s.
- **Top-level state:** `missing_fields` (a list of keys) can go straight into `<GapQuestions missingFields=…>`. When `VoiceRecap` calls `onConfirm(profile)`, Person 4 sets the top-level `confirmed: true`.
- **Ownership:** CLAUDE.md gives the `/onboarding/turn` *extraction logic* to Person 2. A working version is in `voice/onboarding.py` so voice can run end to end. Person 2 can take over the prompt and schema there.
- **README:** "a microphone is visible on every screen". Each voice screen has its own `MicButton`; Person 4 should keep one on the other screens too.

## Proposed additions to the CLAUDE.md endpoint table
| Endpoint | Does |
|---|---|
| `POST /recap/correct` | spoken correction during the recap → which field and its new value (or "confirm all") + reply |
| `POST /voice/tts` | text → WAV audio (frontend falls back to speechSynthesis on failure) |

## Other things to agree with the team
- **Skipped fields** carry `"skipped": true` in the profile entry; corrected/confirmed fields carry `"user_confirmed": true`.
- **Person 2's `/form/gaps`**: return `missing_fields` as `[{field, description}]` if possible. A plain list of keys works too, but the questions sound better with a description.
- **ID scan**: pass `onScanRequest` to `VoiceOnboarding` (open the camera, call `/profile/extract`, merge, resolve with the new profile). The conversation then continues from what's still missing.
- **Immigration/citizenship** fields are refused by `/voice/question` (400). Put them in `blank_fields` for `/recap` so the outro tells the user to fill them in with a caseworker or legal aid.
