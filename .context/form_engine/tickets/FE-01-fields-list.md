# FE-01: Field list for P2 (`sdge_care.fields.json`)
Wave 1 · Depends on: nothing · Size: small · Read first: `../00-contract.md`

**Goal:** a plain JSON file listing every canonical form key, so P2's `/form/gaps` can compare it with the user's profile.

**Write only:** `form_engine/sdge_care.fields.json`

**Format:** a JSON object, `{"form_id": "sdge_care", "fields": [ ... ]}`. Each entry:
```json
{"key": "account_number", "label": "SDG&E Account Number", "kind": "text|checkbox|signature",
 "profile_key": "sdge_account_number", "source": "profile|gap|derived|signature", "required": true}
```
- `key`: exactly the canonical key from the contract (36 in total: 11 text, 24 checkbox, 1 signature).
- `label`: the wording printed on the form (read it with `uv run python -I` from `form_engine/sdge_care.pdf`, `pypdf`).
- `profile_key`: the profile key from the contract mapping table, or `null` for derived/signature fields.
- `source`: `profile` (comes from onboarding), `gap` (not collected at onboarding; must be asked by voice, e.g. `account_number`, `home_phone`), `derived` (computed: `adults`, `children`, `annual_income`, `date`, `contact_*`), `signature`.
- `required`: true only if SDG&E cannot process the form without it (name, address, account_number, household_total, annual_income or a 2A box, signature, date). Checkboxes are never required individually.

**Acceptance**
- File is valid JSON and loads with `json.load`.
- Every canonical key from the contract appears exactly once; no extra keys.
- `uv run python -I -c "import json;d=json.load(open('form_engine/sdge_care.fields.json'));print(len(d['fields']))"` prints the expected count.
- The `gap` list contains `account_number`.
