# CLAUDE.md — "Tell Us Once" (working name)

**First, read `.context/README.md`**. Keep `.context` up to date whenever our understanding changes, a decision is made, or a question the user asks gets an answer worth keeping.

Built for **UCSD Hack for Humanity 2026**, a one-day hackathon (Sat Nov 7, 2026). Hacking runs **11:30 AM to 3:30 PM (about 4 hours)**; projects are **due 3:30 PM**, demos and judging 4:00-5:30. Theme: benefit the city of San Diego. Required tech: **Gemini API**. Judged on Impact for San Diego, Technical (does it work), Creativity, Use of AI, and Demo clarity. Teams of 3+.

## What we're building

A web app that helps immigrants, and anyone who struggles with English paperwork, find and fill out forms in their own language, mainly by voice.

**User flow:**
1. **Onboarding by voice (tell us once).** On first visit the user picks a language, then **talks** with the app instead of typing. Gemini asks the onboarding questions out loud in their language, one at a time, and fills the profile from their spoken answers (see "Onboarding information" below). The user can also photograph an ID, pay stub or old bill to answer some questions without talking. There is no typing form for onboarding. The only fallback is editing a value on the review screen.
2. **Choose a path:**
   - **A. "I have a form."** The user uploads a form, or picks one from our supported list, and we fill it from their profile.
   - **B. "Find forms I qualify for."** Gemini, grounded in Google Search, finds San Diego and California programs the user *may* qualify for based on income range, household and demographics. The user picks one to fill.
3. **Fill form-specific gaps by voice.** The general profile covers most fields. Gap filling is **only** for details a particular form needs that onboarding doesn't collect (e.g. the SDG&E account number for CARE, or a child's school for the meal application). The app asks for these out loud in the user's language, records the spoken answer and turns it into a field value. Gap questions never re-ask anything already in the profile.
4. **Recap in their language.** The app reads every field back aloud, highlights fields Gemini wasn't sure about, and lets the user correct anything.
5. **Sign and download.** The user signs on a signature pad, and the app produces the filled PDF.

**Pitch hook:** in many immigrant families, kids end up translating and filling out government forms for their parents. *"A 12-year-old in City Heights shouldn't have to fill out her family's benefits renewal."* Our angle: **forms that put money back in families' pockets**, i.e. benefits eligible families never claim because the paperwork is in English.

## Onboarding information (collected once, by voice)

These are the profile fields onboarding collects. They're chosen to cover the shared fields on our target forms (SDG&E CARE, CalFresh, school meals, MTS PRONTO) and to support program matching in Path B. **Before finalizing, Person 1 checks this list against the actual PDFs** and adds or removes fields.

Gemini asks these as a natural conversation (e.g. "Who lives with you?"), not as a checklist read aloud. Fields marked *optional* can be skipped by saying "skip."

**1. Language & contact**
- Preferred language (chosen on the first screen)
- Phone number
- Email (optional)

**2. Identity**
- Legal first, middle and last name (confirm spelling in English letters)
- Date of birth
- Gender (optional)
- Photo of an ID (optional; used to prefill name, date of birth and address)

**3. Address & housing**
- Home address (street, unit, city, ZIP)
- Mailing address, if different
- Rent or own
- Monthly rent or mortgage (optional; some programs ask for housing costs)

**4. Household**
- Number of people living in the home
- For each person: first name, relationship to the user, date of birth
- Children in school: which school / district (optional; used for meal programs)

**5. Income**
- Total household income: monthly amount or range
- Income sources: job, self-employment, Social Security, disability benefits, child support, other
- How often they're paid (weekly, every 2 weeks, monthly)
- Pay stub photo (optional; used to prefill income)

**6. Current benefits** (many programs grant eligibility automatically if you already get one of these)
- Already enrolled in any of: CalFresh, Medi-Cal, WIC, SSI, free/reduced school meals, other (yes/no for each)

**7. Situations that unlock programs (all optional, skippable)**
- Anyone in the household 65 or older
- Anyone with a disability
- A veteran in the household

### Never collected at onboarding
- **SSN, bank details, utility account numbers:** asked only when a specific form needs them, during gap filling. The user can also say "leave it blank" and write it on the printed form themselves.
- **Immigration or citizenship status:** never asked by the app. If a form asks for it, the field stays blank and the recap tells the user to fill it in with help from a caseworker or legal aid.

## Scope rules (important)

- **No immigration or visa forms.** Mistakes on them can cause serious legal harm, and "notario" fraud already exploits immigrant communities. If a user asks for one, show a message pointing them to accredited legal aid or an immigration attorney. Do not fill it.
- **Start with one real form and do it well:** the **SDG&E CARE** discount application (lowers the energy bill). Stretch goals: CalFresh, the San Diego Unified free/reduced-price meal application, MTS PRONTO reduced fare.
- **Never guarantee eligibility.** Path B says "you *may* qualify," shows the official source link, and tells the user to check with the program.
- **Never hardcode income limits or eligibility rules from memory.** They change every year. Pull them from official sources (`.gov`, `.ca.gov`, `sdge.com`, `sandiegounified.org`, `sdmts.com`) with grounding, and show the source URL.
- **The user always confirms and signs.** Gemini never submits anything. The output is a PDF the user reviews and submits themselves.

## Privacy rules

- Keep profile data **in session memory only**. No database, and no logging of personal info.
- Never write SSNs, ID numbers or income to logs or console output.
- **Use fake data for all testing and the demo** (fake ID, fake pay stub). Never put a teammate's real documents in the demo.
- The UI says plainly: "We don't store your information."

## Architecture

```
form_engine/   P1: PDF filling, field maps, signature stamping
gemini/        P2: Gemini extraction, program matching, gap detection
voice/         P3: audio in/out, onboarding conversation, recap
frontend/      P4: screens, signature pad, demo assets
```

One top-level folder per role. Each person decides what goes inside their own folder and documents it in its `README.md`. Wiring the pieces into one FastAPI app is agreed between owners when needed.

Suggested stack (the team can change it): React + Vite, FastAPI, `google-genai` (official Gemini Python SDK), `pypdf`, `reportlab` (fallback overlay), `signature_pad` (JS).

**Python tooling: `uv`.** `pyproject.toml` and `uv.lock` are at the repo root (Python 3.12, `.python-version`). Installed: fastapi, uvicorn, google-genai, pypdf, reportlab, python-multipart, python-dotenv, pydantic; dev: pytest, httpx, ruff. Run everything with `uv run ...` (e.g. `uv run fastapi dev <entry file>`). Add packages with `uv add`, never `pip install`, and commit `pyproject.toml` + `uv.lock` together. Copy `.env.example` to `.env` for keys.

### Shared data format (everyone reads and writes this)

```json
{
  "language": "es",
  "profile": {
    "full_name":      {"value": "Maria Lopez", "confidence": 0.95, "source": "id_photo"},
    "gender":         {"value": "female",      "confidence": 1.0,  "source": "onboarding_voice"},
    "address":        {"value": "...",         "confidence": 0.9,  "source": "onboarding_voice"},
    "household_size": {"value": 4,             "confidence": 1.0,  "source": "onboarding_voice"},
    "monthly_income": {"value": null,          "confidence": 0,    "source": null}
  },
  "selected_form": "sdge_care",
  "suggested_programs": [
    {"name": "SDG&E CARE", "why": "...", "source_url": "https://...", "form_id": "sdge_care"}
  ],
  "missing_fields": ["monthly_income"],
  "confirmed": false,
  "signature_png": null
}
```

- `source` is one of: `onboarding_voice`, `id_photo`, `document`, `gap_voice`.
- Household members go in `profile.household_members` as a list of `{first_name, relationship, date_of_birth}`.
- Any field with `confidence < 0.8` must be explicitly confirmed by the user in the recap.

### API endpoints (backend)

| Endpoint | Does |
|---|---|
| `POST /onboarding/turn` | user's audio + current profile → updated profile + next spoken question (or `done: true`) |
| `POST /profile/extract` | photo of document → Gemini vision → profile fields with confidence |
| `POST /programs/find` | profile → Gemini + Search grounding → `suggested_programs` |
| `POST /form/gaps` | profile + form → `missing_fields` (form-specific fields only) |
| `POST /voice/question` | missing field + language → question text (+ audio) |
| `POST /voice/answer` | audio + field → parsed value |
| `POST /recap` | profile + language → recap text (+ audio) |
| `POST /form/fill` | profile + signature → filled PDF |

## Gemini implementation notes

- Use the **`google-genai`** SDK (`from google import genai`). The older `google-generativeai` package is deprecated.
- **Don't hardcode a model name in code.** Read it from `GEMINI_MODEL` in `.env` and pick a current Flash model from Google AI Studio at the start. Use a separate env var `GEMINI_TTS_MODEL` for speech output.
- **Structured output:** for extraction, gap-finding and answer parsing, set `response_mime_type="application/json"` with a `response_schema` so responses always parse.
- **Search grounding (Path B):** use the `google_search` tool. On some models grounding can't be combined with a JSON schema, so use **two calls**: (1) a grounded search for programs and their official URLs, then (2) a second structured-output call that turns the results into `suggested_programs`. Keep the source URLs from the grounding metadata.
- **Audio in:** send the recorded audio (webm/wav) straight to Gemini and ask for a transcript plus a parsed value in one structured call.
- **Onboarding loop:** each turn sends the audio and the current profile. Gemini returns the fields it extracted (one answer may fill several, e.g. "it's me, my husband and two kids" fills household size and members) plus the next question to ask, in the user's language. The loop ends when every onboarding field is filled or skipped. Keep turns short: one question at a time.
- **Audio out:** use a Gemini TTS model for questions and the recap. **Fallback:** the browser's `speechSynthesis` API if TTS is slow or fails during the demo.
- **Language:** every user-facing string Gemini writes must be in `language`. Field values that go into the PDF stay in **English/Latin characters** as the form requires (e.g. transliterate names if needed and confirm with the user).
- Keep the API key in `.env` (`GEMINI_API_KEY`) and never commit it. Add `.env` to `.gitignore`.

## PDF filling notes

- List fields first: `PdfReader(path).get_fields()`.
- Map PDF field names to profile keys in `form_engine/<form_id>.field_map.json`.
- Fill with `PdfWriter` + `update_page_form_field_values(...)`, and set `auto_regenerate=False` / NeedAppearances so the values show up.
- **Many government PDFs are not fillable** (scanned or XFA). Fallback: draw text at fixed coordinates with `reportlab` and merge it onto the page. Check this for the CARE form **in the first hour**.
- Signature: the frontend sends the canvas as a PNG, and the backend stamps it onto the signature line with `reportlab`.

## Team split (4 people)

1. **Form engine.** PDF field listing, `field_map`, `/form/fill`, signature stamping, reportlab fallback.
2. **Gemini.** `/onboarding/turn` extraction logic, `/profile/extract`, `/programs/find` (grounding), `/form/gaps`, answer parsing, confidence scores.
3. **Voice & language.** Mic recording, the voice onboarding conversation, `/voice/question`, `/voice/answer`, `/recap`, TTS plus the browser fallback, re-asking when the user says "that's wrong."
4. **Frontend + demo.** Screens (Language → Voice onboarding (+ optional document scan) → Find or Upload form → Voice gap questions → Review → Sign → Download), accessible UI (big buttons, icons, mic always visible, low-confidence fields in yellow), fake demo documents, the pitch and a backup demo video.

## Timeline (hacking ended up 11:30 AM to 3:30 PM; plan below starts at 12:46 PM)

| Time | Goal |
|---|---|
*Re-planned at 12:46 PM (2h 44m left). The repo had no code yet at that point.*

| Time | Goal |
|---|---|
| 12:46–1:05 | **Now:** lock the shared JSON format, get the Gemini key working (one test call each for audio-in and a Spanish clip), **check whether the CARE PDF is fillable** (reportlab overlay if not) |
| 1:05–2:00 | Each person builds their section against mocks (`?mock=true`) using fake data in the shared format |
| **2:00** | **Checkpoint 1:** Spanish voice onboarding → profile → filled PDF download, even if ugly |
| 2:00–2:45 | Form-specific voice gap questions, recap, frontend wired end to end. **Path B is cut by default**: pick the form from a short list instead |
| **2:45** | **Checkpoint 2:** the full flow works once, start to finish |
| 2:45–3:15 | Fix bugs, make the Spanish demo path reliable, record the backup video by 3:05 |
| 3:15–3:30 | **No new features.** Submit (aim for 3:20, deadline 3:30) |
| 3:30–4:00 | Rehearse the demo twice; demos and judging start at 4:00 |

If a checkpoint is missed by more than 10 minutes, apply the cut order below immediately. The 3:30 submission does not move. Ask an organizer how and where to submit **before 2:30**.

**If behind at Checkpoint 1:** cut multi-language support and demo Spanish only. Then cut Path B before cutting voice. A complete flow in one language beats a half-working app.

## Demo script

1. A Spanish-speaking mom opens the app and chooses Español.
2. The app talks with her in Spanish to build her profile: she answers out loud about her family, address and income, and scans a (fake) ID to skip a few questions.
3. She taps "Find forms I qualify for," and the app suggests SDG&E CARE with an official link.
4. The app asks only for what CARE needs that it doesn't already know (e.g. her SDG&E account number), and she answers by voice.
5. The recap is read back in Spanish, she corrects one yellow field, signs, and the filled PDF downloads.
6. Close: "Tell us once, in your language, and we fill the forms that lower your bills."

## Coding conventions for Claude

- Hackathon speed: simple, working code over abstractions. No auth, no database.
- Every Gemini call: wrap it in try/except, return a clear error to the frontend, and never crash the flow.
- Mock first: each endpoint should have a `?mock=true` mode returning sample JSON so the frontend can be built before the backend is ready.
- Don't make up form field names, program rules or income limits. Read them from the actual PDF or an official source.
