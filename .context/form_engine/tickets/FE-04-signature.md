# FE-04: Signature handling (`signature.py`)
Wave 1 · Depends on: nothing · Size: small · Read first: `../00-contract.md`

**Goal:** safely turn the frontend's base64 canvas PNG into a clean PNG and draw it on a reportlab canvas.

**Write only:** `form_engine/signature.py`, `form_engine/tests/test_signature.py`

**Implement** `decode_signature` and `draw_signature` exactly as in the contract.
- `decode_signature`: accept raw base64 or a `data:image/png;base64,...` URL; `None`, `""` -> return `None`. Invalid base64, or bytes that Pillow cannot open, or a size over 5 MB -> `raise ValueError("invalid signature image")`. Convert to RGBA, **trim fully transparent margins** (use `Image.getbbox()` on the alpha channel; if the whole image is transparent, return `None`), re-encode as PNG bytes. Pillow is already installed as a reportlab dependency; do not add packages.
- `draw_signature(c, png, box)`: `reportlab.lib.utils.ImageReader(BytesIO(png))`, scale to fit `box["w"]` x `box["h"]` keeping aspect ratio, centre it in the box, `c.drawImage(..., mask="auto")`.

**Tests** generate their own PNGs with Pillow in memory (a transparent 200x80 canvas with a black line in the middle; an all-transparent image; garbage bytes). Cover: raw base64, data URL, None, empty string, garbage -> ValueError, all-transparent -> None, trimmed output is smaller than the input, `draw_signature` onto a `reportlab` canvas in `BytesIO` produces a valid non-empty PDF.

**Acceptance:** `uv run pytest form_engine/tests/test_signature.py` passes; ruff clean.
