"""POST /form/fill router."""

import json
import logging
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

router = APIRouter()

MOCK_SESSION = Path(__file__).parent / "fixtures" / "mock_session.json"


class FillRequest(BaseModel):
    session: dict = {}
    form_id: str
    signature_png: str | None = None


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status, content={"error": {"code": code, "message": message}}
    )


@router.post("/form/fill")
def form_fill(req: FillRequest, mock: bool = False):
    session = req.session
    if mock:
        try:
            session = json.loads(MOCK_SESSION.read_text())
        except (OSError, ValueError):
            return _error(500, "mock_unavailable", "Mock session is not available.")
    try:
        from form_engine.fill import UnknownFormError, fill_form

        pdf = fill_form(session, req.form_id, req.signature_png)
    except UnknownFormError:
        return _error(400, "unknown_form", "This form is not supported.")
    except ValueError:
        return _error(400, "bad_input", "The request data could not be used.")
    except Exception as e:  # noqa: BLE001
        logging.getLogger(__name__).error("fill failed: %s", type(e).__name__)
        return _error(500, "fill_failed", "Could not fill the form. Please try again.")
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="sdge_care_filled.pdf"'},
    )
