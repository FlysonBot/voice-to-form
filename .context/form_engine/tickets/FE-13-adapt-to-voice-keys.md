# FE-13: Read the profile keys P3 (voice) actually produces
Wave 4 · Runs AFTER FE-10 finishes (same file) · Read first: `../00-contract.md`

P3's branch `origin/claude/nice-dirac-inofg7` defines the real onboarding profile keys in `voice/fields.py` (read it with `git show origin/claude/nice-dirac-inofg7:voice/fields.py`; read-only git is allowed for this ticket, nothing else). Our `values.py` guessed different names. Make `values.py` read both, keeping our drafts as fallbacks.

**Write only:** `form_engine/values.py`, `form_engine/tests/test_values.py`.

**Do** (each with a test, using inline session dicts shaped like P3's):
1. **Name:** if `full_name` is missing or empty, build it from `first_name`, `middle_name`, `last_name` (values may be `{value, confidence, source}` entries; skip empty parts). When the parts exist they win over a stale `full_name`.
2. **Address:** if `address` is missing, or the parts exist, build `"<address_street> <address_unit>, <address_city>, CA <address_zip>"` from `address_street`, `address_unit` (optional), `address_city`, `address_zip`. Skip empty parts; if street, city or zip is missing and no `address` exists, leave `address` absent.
3. **Benefits:** P3 stores booleans `benefits_calfresh`, `benefits_medi_cal`, `benefits_wic`, `benefits_ssi`, `benefits_school_meals` (each a `{value: true|false}` entry) and `benefits_other` (free text). Map true ones to `pa_calfresh`, `pa_medicaid`, `pa_wic`, `pa_ssi`, `pa_nslp`. Keep the existing `current_benefits` support too; the union of both wins. Free text `benefits_other` goes through the same slug aliases (e.g. "liheap", "calworks"); unknown text ignored.
4. **Income sources:** P3 stores `income_sources` as ONE comma-separated string such as `"job, self-employment, social security"`. Split on commas (and ` and `), then apply the existing slug/alias mapping. Lists and dicts keep working.
5. **Gap keys:** `account_number` reads `sdge_account_number` (already) and `home_phone` reads `home_phone` (already); add a test confirming P3-style `{"value": "123..."}` entries work.
6. **Household members:** P3 stores `household_members` as a plain list directly at `profile["household_members"]` (not wrapped in `{value}`); confirm this path, plus the user's own `household_size` (int), works through the household count logic from FE-10.
7. **Document the key table** at the top of `values.py` (a comment block listing every profile key read and which form key it feeds).

**Acceptance:** `uv run pytest form_engine/tests/test_values.py` passes; ruff clean; existing tests still pass. Report anything in `voice/fields.py` that the form needs but P3 does not produce.
