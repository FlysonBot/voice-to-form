# Form engine contract (read this first; every ticket depends on it)

Goal: `fill_form(session, "sdge_care", signature_b64) -> PDF bytes` and `POST /form/fill`. The form (`form_engine/sdge_care.pdf`, SDG&E Form 142-740 rev 0326) is a **flat, non-fillable** 1-page PDF, 612x792 pt. We draw text/checkmarks/signature onto a transparent overlay (`reportlab`) and merge it onto the blank page (`pypdf`).

## Rules for every ticket
- Python via `uv run`. Run tests with `uv run pytest <your test file>`; lint with `uv run ruff check <your files> && uv run ruff format <your files>`.
- Edit **only the files your ticket lists**. Do not touch other tickets' files, `pyproject.toml`, `CLAUDE.md`, or `API.md`. Need a new dependency? Stop and report instead.
- **No git operations.** The owner commits.
- Fake data only. Never log personal info. No network calls.
- The PDF came from the internet: when parsing it in Python use `uv run python -I`.
- Hackathon speed: simple, working code. No abstractions beyond this contract.
- Finish with a short report: files written, command(s) run and their result, anything you could not do.

## File layout (all under `form_engine/`; one owner per file)
| File | Ticket |
|---|---|
| `sdge_care.fields.json` | FE-01 |
| `sdge_care.layout.json` | FE-02 |
| `render.py`, `tests/test_render.py` | FE-03 |
| `signature.py`, `tests/test_signature.py` | FE-04 |
| `values.py`, `tests/test_values.py` | FE-05 |
| `fixtures/mock_session.json`, `fixtures/test_signature.png` | FE-06 |
| `routes.py`, `tests/test_routes.py` | FE-07 |
| `fill.py`, `tests/test_fill.py` | FE-08 |
| `tests/test_e2e.py` | FE-09 |
Already exist: `__init__.py`, `tests/__init__.py`, `sdge_care.pdf`, `README.md`.

## Canonical form keys (the form-side vocabulary; fixed, do not rename)
**Text** (value is a `str`):
`name`, `home_phone`, `mobile_phone`, `address` (one box: street, apt, city, ZIP), `account_number`, `email`, `adults`, `children`, `household_total`, `annual_income`, `date`
**Checkbox** (value is a `bool`):
- Section 2A (public assistance): `pa_bia`, `pa_calfresh`, `pa_calworks`, `pa_liheap`, `pa_medicaid`, `pa_nslp`, `pa_ssi`, `pa_tribal_tanf`, `pa_wic`, `pa_headstart`
- Section 2B (income sources): `inc_wages`, `inc_rent`, `inc_pensions`, `inc_socsec`, `inc_ssi_ssdi`, `inc_disability`, `inc_unemployment`, `inc_scholarships`, `inc_interest`, `inc_support`, `inc_settlements`, `inc_cash`
- Contact preference: `contact_email`, `contact_mail`
**Signature**: `signature` (an image box)

The printed income line is `$ ___,___ .00` (cents already printed), so `annual_income` is a whole-dollar string like `"38,400"`.

## Layout file schema (`sdge_care.layout.json`, written by FE-02, read by FE-03)
Coordinates are PDF points, origin at the **bottom-left** of the page.
```json
{
  "form_id": "sdge_care",
  "pdf": "sdge_care.pdf",
  "page_size": [612, 792],
  "fields": {
    "name":        {"kind": "text", "page": 0, "x": 72.0, "y": 640.0, "font_size": 10, "max_width": 200},
    "pa_calfresh": {"kind": "checkbox", "page": 0, "x": 60.0, "y": 500.0, "size": 9},
    "signature":   {"kind": "signature", "page": 0, "x": 72.0, "y": 90.0, "w": 180, "h": 36}
  }
}
```
- `text`: `x,y` is the left end of the text baseline. Text wider than `max_width` is shrunk down to a minimum font size of 6, then truncated.
- `checkbox`: `x,y` is the lower-left corner of the printed box, `size` its side. A true value draws a check mark inside it.
- `signature`: lower-left corner plus width/height. The image is scaled to fit inside, keeping its aspect ratio.
- Every canonical key above must appear exactly once.

## Python interfaces (so tickets can be built in parallel)
```python
# render.py  (FE-03)
def render_overlay(layout: dict, values: dict[str, str | bool | None],
                   signature_png: bytes | None = None) -> bytes
    """One-page transparent overlay PDF the same size as layout['page_size']."""
def merge_onto_form(blank_pdf_path: str, overlay_pdf: bytes) -> bytes
    """Overlay merged onto page 0 of the blank form; returns the final PDF bytes."""

# signature.py  (FE-04)
def decode_signature(b64: str | None) -> bytes | None
    """Base64 (optionally a data: URL) -> clean PNG bytes (transparent margins trimmed,
    flattened to RGBA). None/empty -> None. Invalid data -> raises ValueError."""
def draw_signature(c, png: bytes, box: dict) -> None
    """Draw onto a reportlab canvas inside box {x,y,w,h}, keeping aspect ratio."""

# values.py  (FE-05)
def build_form_values(session: dict, today: datetime.date | None = None) -> dict[str, str | bool]
    """Profile session -> value for each canonical key. Missing information -> key absent
    or '' / False. Never invents a value."""

# fill.py  (FE-08)
def fill_form(session: dict, form_id: str, signature_b64: str | None = None) -> bytes
    """Loads layout, builds values, decodes signature, renders, merges. Raises
    UnknownFormError (a ValueError subclass) for an unsupported form_id,
    and ValueError for a bad signature."""
```

## Profile -> form key mapping (DRAFT, the team has not fixed the profile key names yet)
`session` is the shared JSON from `CLAUDE.md`: `{"language", "profile": {key: {"value", "confidence", "source"}}, ...}`. FE-05 keeps ALL profile key names in one dict at the top of `values.py` so they are easy to change. Read only `.value`. Assumed profile keys:

| Profile key | Used for |
|---|---|
| `full_name` | `name` |
| `phone` | `mobile_phone` |
| `home_phone` (optional) | `home_phone` |
| `email` | `email` (and `contact_email` if present) |
| `address` (one string) | `address` |
| `sdge_account_number` (gap question) | `account_number` |
| `household_size` (int) | `household_total` |
| `household_members` (list of `{first_name, relationship, date_of_birth}`) | `children` = members under 18 on `today` |
| `monthly_income` (number) | `annual_income` = x12 |
| `income_sources` (list of strings) | `inc_*` boxes (mapping in FE-05) |
| `current_benefits` (list of strings) | `pa_*` boxes (mapping in FE-05) |

Derived: `adults = household_total - children`; `contact_email` if an email exists, else `contact_mail`; `date` = today as `MM/DD/YYYY`.

## Error shape (DRAFT, owner to agree with the team)
`{"error": {"code": "<snake_case>", "message": "<human readable>"}}` with HTTP 400 (bad input) or 500 (unexpected). Never return a partial PDF.
