# FE-08: `fill_form` integration (`fill.py`)
Wave 2 · Depends on: FE-02, FE-03, FE-04, FE-05 (and FE-06 for tests) · Size: small · Read first: `../00-contract.md`

**Goal:** glue the modules into the one function the router calls.

**Write only:** `form_engine/fill.py`, `form_engine/tests/test_fill.py`

**Implement**
- `class UnknownFormError(ValueError)`.
- `fill_form(session, form_id, signature_b64=None) -> bytes`:
  1. `form_id` must be `"sdge_care"` (a dict `FORMS = {"sdge_care": ("sdge_care.layout.json", "sdge_care.pdf")}` next to the file), else `UnknownFormError`.
  2. Paths relative to this file's folder (`Path(__file__).parent`), not the cwd.
  3. Load layout JSON once (module-level cache is fine), `values = build_form_values(session)`, `png = decode_signature(signature_b64)`, `overlay = render_overlay(layout, values, png)`, return `merge_onto_form(pdf_path, overlay)`.
- Do not write files to disk. Do not log. Let `ValueError` from the signature propagate.

**Tests:** use `fixtures/mock_session.json` and `fixtures/test_signature.png` (base64-encode it in the test): output starts with `%PDF`, has 1 page, extracted text contains "Maria Lopez" and "38,400", works with `signature_b64=None`, unknown form raises `UnknownFormError`, bad signature raises `ValueError`.

**Acceptance:** `uv run pytest form_engine/tests/test_fill.py` passes; ruff clean. If a Wave 1 module is missing or does not match the contract, stop and report which one.
