# voice-to-form ("Tell Us Once")

An app that helps people who aren't comfortable with English fill out official forms **in their own language, by voice**, using AI. The result is the real form, filled in and ready for the person to review, sign and submit themselves.

Built for **UCSD Hack for Humanity 2026**, a one-day hackathon, using the **Google Gemini API**.

## The problem

In many San Diego families, children end up translating and filling out government and utility paperwork for their parents. Benefits that could lower a family's bills, such as SDG&E's CARE energy discount, go unclaimed because the application is in English and the process is confusing. A 12-year-old in City Heights shouldn't have to fill out her family's benefits paperwork.

## What it does

- **Tell us once.** The user talks with the app in their own language. It builds a profile (name, address, household, income) from what they say, and can read some details off a photo of an ID or pay stub.
- **Fill the form.** The app fills the real official form from that profile. It asks only for details a specific form needs that it doesn't already know.
- **Check it together.** Everything is read back in the user's language. Anything the AI wasn't sure about is highlighted for the user to confirm or correct.
- **The user stays in control.** The user signs, and the app produces a PDF. It never submits anything for them.

**Starting form:** the SDG&E CARE discount application. Other forms (CalFresh, school meals, MTS PRONTO reduced fare) are stretch goals.

**What it deliberately does not do:** it does not fill immigration or visa forms, does not guarantee anyone qualifies for a program, and does not store personal information.

## Walkthrough: a first-time user

Meet Maria, a Spanish speaker in San Diego. She has never used the app.

1. **She opens the app and picks her language.** The first screen has big buttons and few words. She taps **Español**. A microphone is visible on every screen.

2. **The app talks with her, in Spanish.** Instead of a typing form, it asks questions out loud, one at a time, like a conversation: who lives with her, her address, her household's income. She answers by speaking. One answer can fill several fields, so "somos cuatro, mi esposo, yo y dos niños" fills in her household size and its members.

3. **She can skip some questions with a photo.** If she'd rather not talk through everything, she photographs an ID or a pay stub and the app reads the name, address or income from it. She can say "skip" for optional questions.

4. **She chooses what to do next.**
   - **"I have a form":** she uploads one, or picks it from the list of supported forms.
   - **"Find forms I qualify for":** the app suggests San Diego and California programs she **may** qualify for, based on her profile, with a link to the official source. It never promises eligibility.

   She taps "Find forms I qualify for", and the app suggests **SDG&E CARE**.

5. **The app asks only what's missing.** The profile already covers most of the form. For anything the CARE form needs that it doesn't know yet, such as her SDG&E account number, the app asks out loud and she answers by voice. It never re-asks something she already said. If she'd rather not share something sensitive, she can say "leave it blank" and write it on the printed form herself.

6. **She checks everything in Spanish.** The app reads every field back to her. Fields it wasn't sure about are highlighted in **yellow**. She says one is wrong, and the app asks again until it's right.

7. **She signs and downloads.** She signs on the screen with her finger. The app fills in the official English form and gives her the **PDF**. She reviews it and submits it to SDG&E herself.

8. **She's done, and nothing is kept.** The app shows "We don't store your information." Her profile lived only in that browser session.

## How it works (for developers)

```
form_engine/   PDF filling and field maps
gemini/        Gemini extraction, program matching, gaps
voice/         audio in/out, onboarding conversation, recap
frontend/      React (Vite): screens, signature pad
```

- **One shared JSON profile** that every part of the app reads and writes. Each field has a value, a confidence from 0 to 1 and a source (voice, ID photo, document). Any field under 0.8 confidence must be confirmed by the user.
- **Gemini** (`google-genai`) transcribes speech, extracts data from photos, parses answers and writes the questions in the user's language, using structured JSON output. Program suggestions use Google Search grounding so income limits and rules come from official sources.
- **PDF filling** uses `pypdf` to fill the form's fields, with `reportlab` to overlay text if the PDF isn't fillable. The signature is stamped on from the on-screen pad.
- **Speech out** uses a Gemini speech model, with the browser's speech synthesis as a fallback.

Full details (data format, API endpoints, team split, timeline, privacy rules) are in [`CLAUDE.md`](CLAUDE.md).

## Setup

Needs [uv](https://docs.astral.sh/uv/) (it installs Python 3.12 for you).

```bash
uv sync                      # create .venv and install everything from uv.lock
cp .env.example .env         # then fill in GEMINI_API_KEY and GEMINI_MODEL
uv run fastapi dev <entry file>   # run the API (entry file TBD by the team)
uv run pytest                # tests
uv run ruff check . && uv run ruff format .
```

Add a package with `uv add <name>` (dev-only: `uv add --dev <name>`), then commit both `pyproject.toml` and `uv.lock`. Never use `pip install`. The frontend (`frontend/`) uses npm and is set up separately.

## Privacy

- Profile data stays in session memory only. There is no database and no logging of personal information.
- Tests and demos use **fake** data only.
- Never commit API keys. Keep `GEMINI_API_KEY` in `.env`.

## Status

Hackathon prototype, built in about four hours. Not a legal service and not an official application channel. Always check a form and its eligibility rules with the program itself.
