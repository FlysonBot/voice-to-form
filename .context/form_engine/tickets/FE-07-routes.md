# FE-07: `POST /form/fill` router (`routes.py`)
Wave 1 · Depends on: nothing (stubs `fill_form` in tests) · Size: medium · Read first: `../00-contract.md`, `../../../API.md` (the `/form/fill` section)

**Goal:** the HTTP endpoint as a FastAPI `APIRouter`, so wiring into the app later is one `include_router` line.

**Write only:** `form_engine/routes.py`, `form_engine/tests/test_routes.py`

**Implement** `router = APIRouter()` with `POST /form/fill`.
- Request JSON: `{"session": {...}, "form_id": "sdge_care", "signature_png": "<base64>" | null}`. Use a Pydantic model (`session: dict`, `form_id: str`, `signature_png: str | None = None`).
- Query param `mock: bool = False`. When true: ignore the body's session, load `form_engine/fixtures/mock_session.json` (**FE-06 creates it in parallel**; if missing at call time return the error shape with code `mock_unavailable`), use `signature_png` from the body if given.
- Call `fill_form` imported **lazily inside the handler**: `from form_engine.fill import fill_form, UnknownFormError` (FE-08 writes it later). In tests, monkeypatch/stub `sys.modules["form_engine.fill"]` with a fake module so your tests never need FE-08.
- Success: `Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": 'attachment; filename="sdge_care_filled.pdf"'})`.
- Errors, using the shape in the contract: `UnknownFormError` -> 400 `unknown_form`; `ValueError` -> 400 `bad_input`; any other exception -> 500 `fill_failed` with a generic message. **Never include request data in error messages or logs** (no personal info).
- No auth, no database, no file saved to disk.

**Tests** (FastAPI `TestClient` on a throwaway `FastAPI()` app that includes only your router): success returns `application/pdf` bytes from the stub; `mock=true` path; unknown form -> 400; ValueError -> 400; unexpected exception -> 500 with no request data in the body; missing `form_id` -> 422.

**Acceptance:** `uv run pytest form_engine/tests/test_routes.py` passes; ruff clean.
