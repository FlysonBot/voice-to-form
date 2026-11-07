# FE-06: Fake session and test signature (`fixtures/`)
Wave 1 · Depends on: nothing · Size: small · Read first: `../00-contract.md`

**Goal:** fake data for tests, `?mock=true` and the demo. **No real people's data.**

**Write only:** `form_engine/fixtures/mock_session.json`, `form_engine/fixtures/test_signature.png`

**`mock_session.json`:** a full session in the shared format from `CLAUDE.md` (`language: "es"`) using the draft profile keys in the contract: `full_name` ("Maria Lopez"), `phone` ("6195550123"), `email`, `address` ("123 Fake St Apt 4, San Diego, CA 92105"), `sdge_account_number` ("123456789012"), `household_size` (4), `household_members` (2 children and 1 spouse, hardcoded DOBs: 2018-05-01, 2014-09-15 and 1985-03-02), `monthly_income` (3200), `income_sources` (["job"]), `current_benefits` (["calfresh", "school_meals"]). Each profile entry has `value`, `confidence` (1.0, except make one 0.6), `source`. Other top-level keys as in the CLAUDE.md example (`selected_form: "sdge_care"`, `missing_fields: []`, `confirmed: true`, `signature_png: null`, `suggested_programs: []`). All data obviously fake (phone 555 prefix).

**`test_signature.png`:** generate with Pillow (a script run once, not committed): 300x120 transparent RGBA with a black wavy pen line (a polyline with a few points, width 3) so it looks like a signature. Keep under 20 KB.

**Acceptance**
- `json.load` works; every profile key from the contract table (except optional `home_phone`) is present; DOBs are valid ISO.
- `PIL.Image.open` opens the PNG, mode RGBA, not fully transparent.
