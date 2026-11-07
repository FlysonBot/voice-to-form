# gemini

**Owner:** P2 Gemini

**Scope (from CLAUDE.md):** /onboarding/turn extraction logic, /profile/extract, /programs/find (grounding), /form/gaps, answer parsing, confidence scores.

## Status

| Piece | State |
|---|---|
| Audio → structured JSON core (`client.call_audio_json`) | Done, tested against real Gemini with browser-style webm/opus clips (no conversion needed) |
| `POST /onboarding/turn` | Done. Real call: Spanish greeting turn, and "somos cuatro, mi esposo José y dos hijos" → household_size 4 + 3 members |
| `POST /voice/answer` (answer parsing) | Done. Real call: spoken Spanish account number → correct digits |
| `/profile/extract`, `/form/gaps`, `/programs/find` | Not started |

## Layout

```
gemini/
  client.py          call_audio_json(): audio (optional) + prompt → validated Pydantic object.
                     Inline audio, JSON schema output, one retry (optional fallback model),
                     GeminiError(retryable).
                     Logs only model/latency/error class, never personal data.
  profile_fields.py  ONBOARDING_FIELDS: the profile key catalog (single source of truth),
                     coerce_value(), merge_updates(), remaining_fields(), monthly income math
  schemas.py         Gemini response schemas + API request/response models
  prompts.py         System prompts and prompt builders (iterate here)
  onboarding.py      run_onboarding_turn(): one voice onboarding turn
  voice_answer.py    parse_voice_answer(): one gap-filling answer → typed value
  router.py          FastAPI APIRouter with both routes (mount this in the team app)
  dev_app.py         Standalone app to run only these routes
  mocks/             Sample responses returned by ?mock=true
  scripts/try_audio.py  CLI to run a local clip through any of the calls
  scripts/live_e2e.py   Live end-to-end test: full fake Spanish conversation + gap fields
                        against real Gemini, with PASS/FAIL checks (costs a few cents)
  tests/             pytest (no API key needed)
```

## Run

From the repo root (`.env` at the root needs `GEMINI_API_KEY` and `GEMINI_MODEL`):

```bash
uv run fastapi dev gemini/dev_app.py          # only these routes, http://localhost:8000/docs
uv run pytest gemini                          # no key needed
uv run python gemini/scripts/try_audio.py gemini/samples/test.webm --mode transcribe
uv run python gemini/scripts/try_audio.py --mode onboarding --lang es    # first turn, no audio
uv run python gemini/scripts/live_e2e.py        # live test, needs macOS `say` + ffmpeg
```

Put test recordings (FAKE data only) in `gemini/samples/`; that folder is gitignored.

**webm:** Gemini accepted `audio/webm` (opus) directly in testing. If that ever breaks, install ffmpeg and set `AUDIO_CONVERT_TO_WAV=1` in `.env`; `client.py` then converts every clip to 16 kHz mono WAV first.

## Live test results (2026-11-07, `gemini-3.1-flash-lite`)

`live_e2e.py` passes 61/61 checks: an empty profile filled by 16 spoken Spanish answers (phone, skip, spelled name, date, address, a ZIP **correction**, household + member birthdays, school, income, benefits, situations), then 5 gap fields (account number, "leave it blank" for SSN, yes/no, date, an unclear answer that gets a re-ask). About 2.5 s per onboarding turn, 1.4 s per gap answer.

Design choices that came out of it:
- **Onboarding uses two calls per turn:** (1) transcribe the audio, given only the question just asked and a list of local words (Medi-Cal, CalFresh, San Diego Unified…); (2) extract fields + next question from that text. One combined audio call misheard values (a ZIP correction came back as the already-known ZIP, "junio" became "julio"); transcription with no context misheard short answers ("mujer" → "morir") and place names ("San Diego Unified" → a district in Lima).
- **Never put known profile values in the transcription prompt;** they bias what Gemini hears.
- **Names not spelled out letter by letter are capped at confidence 0.7,** so the recap asks the user to confirm them (Gemini rated everything 1.0).
- Optional free-text answers meaning "nothing" ("no", "nada") count as a skip, not a value.

## Models and quota (read before the demo)

- **Free tier limits are tiny:** `gemini-3.5-flash` allowed **5 requests/minute and 20 requests/day** per project. One onboarding conversation is 15+ requests, so the free tier cannot carry testing plus a demo. **Billing is now enabled** on P2's project (prepaid credit, ~2:15 PM), so that key has Tier 1 limits. With prepay, a $0 balance makes every call fail with HTTP 402 ("prepayment credits are depleted"), even free-tier ones. A full onboarding run costs a few cents on `gemini-3.1-flash-lite`.
- Each model has its own quota. `GEMINI_FALLBACK_MODEL` in `.env` (optional) is used for the retry when the main model fails (429/5xx/timeout); otherwise the retry waits the delay the API asks for (max 10 s).
- What we saw on 2026-11-07 ~1:30 PM: `gemini-3.8-flash` and `gemini-3.7-flash` returned 503/504 (overloaded); `gemini-2.5-flash` is gone (404); `gemini-3.5-flash` worked (~2-3 s) until the daily quota ran out; `gemini-3.1-flash-lite` worked and gave correct results on our test clips. No TTS model is available to this key: `gemini-3.8-flash-lite-tts` and `gemini-3.8-flash-tts` return 404 via the Interactions API even with billing on (P3: use browser `speechSynthesis`).
- Number fields (`digits`, `phone`, `zip`) in `/voice/answer` use a deliberately short prompt (`prompts.number_answer_system`). The general prompt garbled spoken digit strings ("cero uno dos tres" → "0003…") in 6 of 6 runs; the short one got them right.

To mount in the team's combined app:

```python
from gemini.router import router as gemini_router

app.include_router(gemini_router)
```

## API contracts

The full request/response contracts for `/onboarding/turn` and `/voice/answer` are in [`../API.md`](../API.md) (the team's single source). In short:

- Both take `multipart/form-data`: `audio` (file) plus `session` (JSON string, the shared data format; unknown keys are ignored). `/voice/answer` also takes `field` (JSON string) and an optional `question`.
- Onboarding reads two extra session keys: `skipped` and `last_question`.
- The backend is **stateless**; the client sends the session every call.
- Errors: `{"error": "...", "retryable": bool}`. Sample responses: `mocks/`.
- `done`, `monthly_income` and type validation are computed here, not trusted from Gemini. Corrections overwrite; otherwise a lower-confidence value never replaces a higher-confidence one (e.g. from an ID photo).

## Profile keys

Names and addresses are split into separate keys (decided; there is no `full_name` or `address` key). The catalog:

`phone`, `email`, `first_name`, `middle_name`, `last_name`, `date_of_birth`, `gender`, `address_street`, `address_unit`, `address_city`, `address_zip`, `mailing_address` (`"same_as_home"` if same), `housing_status`, `monthly_housing_cost`, `household_size`, `household_members` (list of `{first_name, relationship, date_of_birth}`, excluding the user), `children_schools`, `income_amount`, `income_frequency`, `income_sources`, `monthly_income` (computed), `benefits_calfresh`, `benefits_medi_cal`, `benefits_wic`, `benefits_ssi`, `benefits_school_meals`, `benefits_other`, `has_senior_65_plus`, `has_disability`, `has_veteran`.

Types and descriptions are in `profile_fields.py`.

## Hand-offs

- **P1 form_engine:** map PDF fields to the keys above in your `field_map`. There is no state key: write "CA" into the form's State field yourself. Values are already normalized (dates `YYYY-MM-DD`, phone 10 digits, ZIP 5 digits, Latin-letter names).
- **P3 voice:** record audio, call the two routes, speak `next_question` / `clarification_question`. `/voice/answer` lives here because answer parsing is P2's scope; if you'd rather own the route, call `gemini.voice_answer.parse_voice_answer()` from your code instead.
- **P4 frontend:** keep the whole session (including `skipped` and `last_question`) in React state and send it as the `session` field on every call; after each onboarding turn, copy back `profile` and `skipped` and set `last_question = next_question`; show fields with `confidence < 0.8` in yellow. Use `?mock=true` until the real calls work.
