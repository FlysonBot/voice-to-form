# FE-11: Per-digit income boxes and a taller signature box
Wave 3 · Parallel with FE-10, FE-12 · Read first: `../00-contract.md`

**Write only:** `form_engine/sdge_care.layout.json`, `form_engine/render.py`, `form_engine/tests/test_render.py`. Do not edit other files (the income assertions in `test_fill.py`/`test_e2e.py` will be updated by the owner afterwards; tell them in your report).

**Problem:** the printed income field is `$ [ ][ ] , [ ][ ][ ] . 0 0`. `annual_income` ("38,400") is drawn as one free-text string, so digits cross the box dividers. Also the signature box is only 11 pt tall.

**Do**
1. **Comb layout.** Extend the layout schema for `annual_income`: `{"kind": "text", ..., "comb": {"xs": [x_center_of_each_digit_box, ...], "align": "right"}}`. Measure the real digit-box centres from the form (render with `pdftoppm -r 288`, measure, as FE-02 did; a reviewer estimated roughly 212.4, 224.1 | 241.2, 252.0, 263.7, but verify against the vector lines). Boxes are left-to-right; the printed comma and `.00` stay untouched.
2. **Renderer.** In `render.py`, when a `text` field has `comb`, draw only the digits of the value (strip every non-digit), right-aligned into the boxes: one digit per box, each centred on its x. If there are more digits than boxes, fall back to the old free-text drawing of the formatted string (keep existing behaviour), and note that in a code comment. No change for fields without `comb`.
3. **Signature box.** Make the `signature` box taller (about 16 pt) while keeping it clear of the printed declaration text and the printed signature line, and check visually. Adjust `y` so it sits just above the line.
4. **Visual verification (required):** render the filled form from `form_engine/fixtures/mock_session.json` through `form_engine.fill.fill_form` (with `form_engine/fixtures/test_signature.png` base64) to PNG at 288 dpi, **look at it** with the Read tool, and confirm each digit of 38,400 sits in its own box and the signature sits on the line. Also test a 5-digit-boundary value (99,999) and a 6-digit value (111,440) and report how they look. Scratch files go under `/tmp/claude-1000/-home-quasar-Data-Projects-MyRepos-aic-hack/1101e837-dadd-486a-8e1f-88355205d6c3/scratchpad/fe11`.

**Tests (`test_render.py`):** add tests with a toy layout: comb digits land at the expected x (check via the drawn operations or by rendering and extracting text positions), more digits than boxes falls back without crashing, non-comb fields unchanged. Existing tests must keep passing.

**Acceptance:** `uv run pytest form_engine/tests/test_render.py` passes; ruff clean; the visual check is described in your report along with the final PNG path. List the exact strings in `test_fill.py` / `test_e2e.py` that assert `"38,400"` against extracted text and say whether they still pass.
