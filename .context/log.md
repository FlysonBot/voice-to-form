# Log (newest last)

- 2026-11-07: Fetched the three MLH pages; explained event to user; asked which track they want (pending).
- 2026-11-07: Created `.context`, `.gitignore`, `CLAUDE.md`.
- 2026-11-07: User says multiple-track submission is allowed (their statement, not on the pages). Decision: enter Track 1 (Best Overall, Hack for Humanity) + Track 2 (Gemini API); skip GitHub Copilot.
- 2026-11-07: Wrote criteria.md (inferred judging model). User: medical-paperwork helper is overdone -> keep as fallback only, seek a unique idea.
- 2026-11-07: Ran comparison; added to criteria.md.
- 2026-11-07: Brainstormed 5 ideas; recommended Parent Voice-to-Form, pantry bag as safe pick. Awaiting user choice.
- 2026-11-07: User shared kickoff slide photos: team min 3 (joined team of 4), projects due 3:30 PM, published rubric, judges, ShorECheck example. Updated event.md/criteria.md. User undecided among ideas 1,3,4,5.
- 2026-11-07: Past-submissions subagent reported (thin). Judges subagent still pending.
- 2026-11-07: Judges subagent reported (thin). Both research tasks done.
- 2026-11-07: User asked for more ideas; added round 2 (6-10).
- 2026-11-07: Cloned https://github.com/FlysonBot/voice-to-form.git into project root (branch main, tracks origin/main). Repo had only .gitignore, LICENSE, README (one-line description: voice-driven form filling for non-English speakers, Streamlit). Appended .context to its .gitignore. Team disliked legal/paperwork ideas; voice-to-form is being considered, concern: making it San Diego-specific.
- 2026-11-07: Team posted a 4-person plan; bet = voice-to-form for SDG&E CARE. Teammates will write the project CLAUDE.md.
- 2026-11-07: Pulled teammates CLAUDE.md ("Tell Us Once": voice onboarding profile, Path A upload form / Path B find programs via Search grounding, gap filling, recap, sign, PDF; target form SDG&E CARE). Merged by appending a .context section. NOTE: it says 6-hour hackathon; real build window is 11:30-3:30 (4h). Its timeline/checkpoints need rescaling.
- 2026-11-07: Fixed CLAUDE.md timeline to the real 11:30-3:30 window (checkpoints 1:45 and 2:45, no new features 3:15, submit 3:30, rehearse 3:30-4:00); moved the ".read .context first" instruction to the TOP of CLAUDE.md (was at the bottom); added event facts (judging criteria, teams 3+). Wrote README.md: project explanation plus first-time-user walkthrough (Maria, Spanish speaker, SDG&E CARE). Nothing committed yet.
- 2026-11-07 12:46 PM: User said timeline was still wrong. Real time was 12:46, 2h44m left, repo had no code, no new remote commits. Re-planned CLAUDE.md timeline from now: checkpoints 2:00 and 2:45, Path B cut by default, backup video by 3:05, submit ~3:20 (deadline 3:30), rehearse 3:30-4:00, ask organizer about submission before 2:30.
- 2026-11-07: Removed named judges from event.md and criteria.md (kept roles and demo advice only), at user request, before first commit.
- 2026-11-07 ~1:05 PM: Set up `uv` (root `pyproject.toml`, `uv.lock`, Python 3.12). Added fastapi, uvicorn, google-genai, pypdf, reportlab, python-multipart, python-dotenv, pydantic; dev: pytest, httpx, ruff. Added `.env.example`. Documented in README (Setup) and CLAUDE.md (Architecture).
- 2026-11-07 ~1:20 PM: Folder structure decided: one top-level folder per role (form_engine/, gemini/, voice/, frontend/), each with a README; owners decide their own internals. Replaces the backend/frontend sketch.
