# Form engine (P1) work area

Everything for the form engine role: contract, backlog, and tickets written so subagents can implement them.

| File | Purpose |
|---|---|
| `00-contract.md` | **Read first.** Canonical form keys, layout schema, Python interfaces, file ownership, rules for agents |
| `BACKLOG.md` | Owner's checklist (human view) |
| `tickets/FE-0N-*.md` | One self-contained ticket per file group |

## Tickets and order
| Ticket | Wave | Writes | Depends on |
|---|---|---|---|
| FE-01 fields list for P2 | 1 | `sdge_care.fields.json` | none |
| FE-02 coordinates (critical path, largest) | 1 | `sdge_care.layout.json` | none |
| FE-03 renderer + merger | 1 | `render.py` + test | none |
| FE-04 signature handling | 1 | `signature.py` + test | none |
| FE-05 profile -> form values | 1 | `values.py` + test | none |
| FE-06 fake session + test signature | 1 | `fixtures/*` | none |
| FE-07 `/form/fill` router | 1 | `routes.py` + test | none (stubs `fill_form`) |
| FE-08 `fill_form` glue | 2 | `fill.py` + test | FE-02, 03, 04, 05, 06 |
| FE-09 end-to-end test + visual QA | 2 | `tests/test_e2e.py` | FE-07, FE-08 |

Wave 1 tickets touch disjoint files and can run at the same time. Wave 2 needs wave 1 merged first.

## Status
Tickets written 2026-11-07 ~1:34 PM. All 9 implemented by subagents and verified (33 tests pass, ruff clean, filled PDF viewed by owner's Claude session). Not yet committed.

Round 2 (FE-10..FE-13, ~2:25 PM): values hardening (label slugs, DOB formats, no-guess household counts, Pacific date, dict address/name, phone, names), per-digit income boxes + taller signature box (13.5 pt), signature pixel limit + white-background trim, route/test hygiene, and `values.py` now reads P3's real keys (`first_name`/`last_name`, `address_*`, `benefits_*` booleans, comma-separated `income_sources`). 56 tests pass. Verified by eye with a P3-shaped profile.

Known issues / follow-ups:
- Income of 100,000 or more (6 digits) does not fit the 5 printed boxes; it falls back to free text that crosses dividers. CARE limits for 7-8 people are above that.
- Section 2A/2B checkboxes are ~5 pt, so check marks are small.
- Several CARE boxes (BIA, CalWORKs, LIHEAP, Tribal TANF, Head Start; income: rent, pensions, unemployment, scholarships, interest, settlements) cannot be set from P3's onboarding fields unless the user names them under `benefits_other`/"other".
- Contact preference is inferred (email if present, else mail); P3 does not ask.
- Error shape and profile format are still DRAFTS with the team; the shared FastAPI entry file does not exist (P3 has `voice/dev_app.py`; P4's Vite proxy expects the API on :8000 without a prefix).
- Not committed yet.
