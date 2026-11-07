# FE-03: Overlay renderer and merger (`render.py`)
Wave 1 · Depends on: nothing (uses a toy layout in tests) · Size: medium · Read first: `../00-contract.md`

**Goal:** turn a layout dict plus values into a one-page transparent PDF overlay, and merge it onto the blank form.

**Write only:** `form_engine/render.py`, `form_engine/tests/test_render.py`

**Implement exactly the two functions in the contract** (`render_overlay`, `merge_onto_form`).
- Use `reportlab.pdfgen.canvas` with `pagesize=tuple(layout["page_size"])`. Font Helvetica.
- `text` kind: draw only if the value is a non-empty `str`. Shrink font size step by step (0.5 pt) until `stringWidth <= max_width`, minimum 6; if it still does not fit, truncate characters until it does (no ellipsis crash).
- `checkbox` kind: if value is `True`, draw a check mark (two lines, or ZapfDingbats `4`) inside the box defined by `x,y,size`. If false/missing, draw nothing.
- `signature` kind: if `signature_png` is given, call `from form_engine.signature import draw_signature` and draw it in the layout box. **FE-04 builds that module in parallel**: import it inside the function and, if the import fails, skip the signature (do not crash). In your tests, monkeypatch `form_engine.render.draw_signature` or insert a stub into `sys.modules`; do not depend on the real file.
- Ignore value keys that are not in the layout; ignore layout keys with no value.
- `merge_onto_form(blank_pdf_path, overlay_pdf)`: with `pypdf`, read the blank, `page.merge_page(overlay_page)`, write to `BytesIO`, return bytes. The result must still have exactly one page of size 612x792.

**Tests (`test_render.py`)** use a small hand-written layout dict (3 text, 2 checkbox, 1 signature) and the real `form_engine/sdge_care.pdf` for the merge test:
- overlay is valid PDF, 1 page, correct size.
- text appears: extract text from the merged result with pypdf and assert the sample value is in it.
- long text does not raise and stays within max_width (check via reportlab `stringWidth` of what you drew; expose a helper `_fit_text(text, font, size, max_width) -> (text, size)` and test it directly).
- merged output has 1 page.

**Acceptance:** `uv run pytest form_engine/tests/test_render.py` passes; ruff clean.
