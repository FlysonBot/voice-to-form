# FE-05: Profile -> form values (`values.py`)
Wave 1 · Depends on: nothing (inline test data) · Size: medium · Read first: `../00-contract.md`

**Goal:** a pure function that turns the shared session JSON into the value for every canonical form key.

**Write only:** `form_engine/values.py`, `form_engine/tests/test_values.py`

**Implement** `build_form_values(session, today=None)`; `today` defaults to `datetime.date.today()`.
- Put ALL profile key names in one dict `PROFILE_KEYS` at the top of the file (so renaming later is a one-line change). Use the draft names in the contract.
- Helper `_val(session, key)`: `session["profile"][key]` may be missing, `None`, or `{"value": ..., ...}`; return the `.value` or `None`. Never raises.
- Text keys: `name`, `mobile_phone` (from `phone`), `home_phone`, `email`, `address`, `account_number`.
  - Convert to English/Latin characters: `unicodedata.normalize("NFKD", s)` then drop combining marks (`María` -> `Maria`); then drop any remaining non-ASCII character. Strip whitespace.
  - Phone: if it has exactly 10 digits, format `(619) 555-0123`; otherwise return the stripped string unchanged.
- Household: `household_total` = `household_size` as a string (if missing, `len(household_members) + 1` when members exist, else absent). `children` = number of members whose `date_of_birth` (ISO `YYYY-MM-DD`; skip unparsable dates) makes them under 18 on `today`. `adults` = `household_total - children`, never below 0. Members may sit at `profile["household_members"]` either as a list or as `{"value": [...]}`, or at `session["household_members"]`; support all three.
- `annual_income` = `monthly_income * 12` as a whole-dollar string with thousands commas (`"38,400"`). Only when `monthly_income` is a number (int/float or numeric string); ranges or text -> absent.
- `date` = `today` as `MM/DD/YYYY`.
- Contact preference: `contact_email` True if an email value exists else `contact_mail` True.
- `current_benefits` (list of strings, case-insensitive) -> `pa_*`: `calfresh`->`pa_calfresh`, `medi_cal`/`medicaid`->`pa_medicaid`, `wic`->`pa_wic`, `ssi`->`pa_ssi`, `school_meals`/`nslp`->`pa_nslp`, `calworks`/`tanf`->`pa_calworks`, `liheap`->`pa_liheap`. Unknown strings ignored. Unlisted boxes are `False`.
- `income_sources` -> `inc_*`: `job`/`wages`/`self_employment`->`inc_wages`, `rent`/`royalty`->`inc_rent`, `pension`->`inc_pensions`, `social_security`->`inc_socsec`, `ssdi`/`ssp`->`inc_ssi_ssdi`, `disability`->`inc_disability`, `unemployment`->`inc_unemployment`, `scholarship`->`inc_scholarships`, `interest`/`dividends`->`inc_interest`, `child_support`/`spousal_support`->`inc_support`, `settlement`->`inc_settlements`, `other`/`cash`->`inc_cash`.
- **Never invent.** Missing input -> the key is absent (text) or `False` (checkbox). Do not read `confidence`. Do not fill `signature`. Do not log anything.

**Tests** use inline dicts (do not depend on the fixtures file). Cover: a full session; a nearly empty session (no crash, only `date`/`contact_mail` set); accents stripped; phone formatting; children by DOB on both sides of the 18th birthday; adults never negative; all three household_members locations; income x12 and a range string (absent); benefit and income mapping; unknown strings ignored.

**Acceptance:** `uv run pytest form_engine/tests/test_values.py` passes; ruff clean.
