# FE-10: Harden `values.py` (review round 1 fixes)
Wave 3 · Parallel with FE-11, FE-12 · Read first: `../00-contract.md`

**Write only:** `form_engine/values.py`, `form_engine/tests/test_values.py`. Do not edit any other file.

**Do** (every item gets a test):
1. **Label normalization.** One helper `_slug(s)`: lowercase, replace every run of non-alphanumerics with `_`, strip `_`. Apply it to every entry of `current_benefits` and `income_sources` before lookup, and to the map keys. Add aliases: benefits `snap`->`pa_calfresh`, `medi_cal`/`medicaid`->`pa_medicaid`, `school_meals`/`free_reduced_school_meals`/`nslp`/`school_lunch`->`pa_nslp`, `ssi`, `wic`, `calworks`/`tanf`, `liheap`, `bia`/`bia_general_assistance`->`pa_bia`, `tribal_tanf`->`pa_tribal_tanf`, `head_start`/`headstart`->`pa_headstart`. Income: `self_employment`, `job`, `wages`, `social_security`, `child_support`, `spousal_support`, `disability`/`disability_benefits`/`workers_compensation`, `pension(s)`, `unemployment`, `rent`/`rental_income`/`royalty`, `scholarship(s)`, `interest`/`dividends`, `settlement(s)`, `cash`/`other` (as in the current map, plus plurals). Also accept a **dict** of `{label: truthy}` for both fields (keep the keys with truthy values), and a single string.
2. **Dates of birth.** Accept ISO date, ISO datetime (`2018-05-01T00:00:00`, ignore time/`Z`), and `MM/DD/YYYY`; unwrap `{"value": ...}` dicts. Anything else -> unknown.
3. **Household counts do not guess.** Write `adults`/`children` only when `household_total` is known AND every member's age is known (all DOBs parsed) AND `len(members) + 1 == household_total` (user plus members) or, if a member has `relationship` in {`self`, `me`, `user`}, `len(members) == household_total`. Otherwise write only `household_total`. If `household_size` is missing, `household_total` falls back to `len(members) + 1` only when members exist.
4. **Date in Pacific time.** `today` default = `datetime.datetime.now(ZoneInfo("America/Los_Angeles")).date()`; if `ZoneInfoNotFoundError`, fall back to a fixed UTC-8 offset. Tests pass `today` explicitly except one that checks the default is a `date`.
5. **Structured values.** For `address`: if the value is a dict, join the present parts in order `street, unit, apt, city, state, zip` with `", "` (street+unit first joined by space); for `full_name`: `first, middle, last` joined by spaces. Any other non-str/number type -> absent (never a repr).
6. **Phone:** a leading `+1` or `1` on 11 digits is stripped before formatting.
7. **Numbers:** reject non-finite and negative `monthly_income` (annual_income absent), and `household_size < 1`.
8. **Names:** before NFKD, translate `Đ`->`D`, `đ`->`d`, `Ø`->`O`, `ø`->`o`, `Ł`->`L`, `ł`->`l`, `ß`->`ss`, curly quotes/apostrophes -> straight. If a name loses more than half its letters (e.g. non-Latin script), return it absent rather than a damaged name.

**Acceptance:** `uv run pytest form_engine/tests/test_values.py` passes with new tests for each item; ruff clean. The existing public behavior (keys, `annual_income` as `"38,400"`, `date` as `MM/DD/YYYY`) is unchanged.
