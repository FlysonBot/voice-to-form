# server

The combined backend: every role's routes in one FastAPI app (`main.py`), plus thin
adapters (`adapters.py`) where the frontend's request/response shape differs from an
owner's contract. Owners' code is called unchanged.

## Run the whole product
```bash
# 1. .env at the repo root (copy .env.example): GEMINI_API_KEY, GEMINI_MODEL, ...
uv run uvicorn server.main:app --reload --port 8000      # terminal 1, repo root

# 2. frontend (terminal 2)
cd frontend && npm install
echo "VITE_API_MODE=live" > .env       # live = real Gemini; server = backend mocks; local = no backend
npm run dev                            # http://localhost:5173 (Chrome; allow the microphone)
```
Optional: `USE_GEMINI_TTS=1` in the root `.env` adds Gemini's voice (`audio_b64`) to
onboarding replies, gap questions and the recap. Off by default; the browser voice is used.

## Who serves what
| Route | Code | Adapter does |
|---|---|---|
| `POST /onboarding/turn` | P2 `gemini.run_onboarding_turn` | accepts the frontend's `text` (typed answer) and `history`; adds `reply`; keeps skipped fields as `{"value": ""}` |
| `POST /voice/answer` | P2 `gemini.parse_voice_answer` | accepts `field` as a bare key (builds P2's GapField); typed `text` answers; "leave it blank" → `""` |
| `POST /voice/question` | P3 `voice.make_question` | reads `session`; adds `text` |
| `POST /recap` | P3 `voice.make_recap` | reads `session`; adds `text`, `needs_confirm`; blank fields mentioned in the outro |
| `POST /recap/correct`, `/voice/tts` | P3 `voice/router.py` | — |
| `POST /form/fill` | P1 `form_engine/routes.py` | — |
| `POST /form/gaps` | `adapters.py` | required `gap` fields in `form_engine/<form_id>.fields.json` missing from the profile |
| `POST /profile/extract`, `/programs/find` | **not built yet** | the frontend shows a "try again" message |

All routes support `?mock=true`.
