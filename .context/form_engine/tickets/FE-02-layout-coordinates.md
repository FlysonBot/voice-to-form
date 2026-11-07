# FE-02: Coordinates for every box (`sdge_care.layout.json`)
Wave 1 · Depends on: nothing · Size: LARGE, critical path · Read first: `../00-contract.md`

**Goal:** find where each canonical key goes on the page and write `form_engine/sdge_care.layout.json` using the schema in the contract.

**Write only:** `form_engine/sdge_care.layout.json` (scratch images go in the scratchpad/temp dir you are given, not the repo)

**How**
1. Render the page to PNG with `pdftoppm -r 144 -png form_engine/sdge_care.pdf <scratch>/page` (144 dpi = scale 2.0, so PDF point = pixel / 2, and y flips: `y_pdf = 792 - y_pixel/2`).
2. Get exact label positions with `pypdf` (`page.extract_text(visitor_text=...)`, which gives the text matrix per fragment) run under `uv run python -I`. The checkbox glyphs show up as separate characters; use their positions for checkbox `x,y`. Printed lines for the name, phone, address, account number, email, date, and signature are underlines: place text just above them.
3. The first block ("Your Name / Home Telephone / Home Address... / SDG&E Account Number / Email Address / Customer Signature / Date") are fill-in lines. Section 1 has `Adults: __ + Children: __ = __` (keys `adults`, `children`, `household_total`). Section 2A has 10 checkboxes (`pa_*`), Section 2B has 12 (`inc_*`) plus the line `Total annual household income: $ ___,___ .00` (`annual_income`; cents are pre-printed, so place the whole-dollar string left of the `.00`). The bottom has `How would you like to be contacted? Email / Mail` (`contact_email`, `contact_mail`).
4. Write the JSON. Pick `font_size` 10 (9 for the address, with `max_width` equal to the printed line length). Checkbox `size` = the printed box side.
5. **Verify visually (required):** write a throwaway script that fills EVERY key with a visible sample value (e.g. `XXXX`, all checkboxes true, a coloured rectangle for the signature) using reportlab, merges it onto the blank, renders to PNG, and **look at the PNG** with the Read tool. Fix coordinates until each mark is inside the right box/line and nothing overlaps printed text. Do this at least twice (coarse, then fine).
6. Do not import `render.py` (another ticket builds it in parallel); use plain reportlab in your throwaway script.

**Acceptance**
- Every canonical key appears exactly once, with valid `kind`/`page`/numbers, per the contract schema.
- A final verification PNG, viewed by you, shows all marks inside their boxes/lines.
- Report: any key you could not place and why (e.g. the Section 2A "Head Start (Tribal Only)" box), plus the final PNG path.
