"""Audio → JSON routes: POST /onboarding/turn and POST /voice/answer.

Both take multipart/form-data:
  audio:    the recorded clip (webm/wav/ogg...). Optional on the first onboarding turn.
  session:  JSON string, the shared data format (schemas.Session); unknown keys ignored.
  /voice/answer also takes `field` (JSON string, schemas.GapField) and an optional
  `question` (the question the user heard).
Add ?mock=true to get sample JSON without calling Gemini. Contract: API.md.

The backend is stateless: the frontend keeps the profile and sends it every turn.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError

from .client import GeminiError
from .onboarding import run_onboarding_turn
from .schemas import GapField, Session, VoiceAnswerState
from .voice_answer import parse_voice_answer

log = logging.getLogger("routes.audio")
router = APIRouter()
MOCKS = Path(__file__).resolve().parent / "mocks"


def _error(status: int, message: str, retryable: bool) -> JSONResponse:
    return JSONResponse(
        status_code=status, content={"error": message, "retryable": retryable}
    )


def _parse_json(raw: str, model: type[BaseModel], name: str):
    try:
        return model.model_validate(json.loads(raw)), None
    except (json.JSONDecodeError, ValidationError) as e:
        # Report only the location of the problem, never the submitted values.
        where = (
            f"{name} is not valid JSON"
            if isinstance(e, json.JSONDecodeError)
            else f"invalid {name}: "
            + ", ".join(".".join(map(str, err["loc"])) for err in e.errors())
        )
        return None, _error(422, where, False)


def _read_audio(audio: UploadFile | None) -> tuple[bytes | None, str | None]:
    if audio is None:
        return None, None
    data = audio.file.read()
    return (data or None), audio.content_type


def _mock(name: str) -> JSONResponse:
    return JSONResponse(json.loads((MOCKS / name).read_text(encoding="utf-8")))


@router.post("/onboarding/turn")
def onboarding_turn(
    session: Annotated[str, Form()],
    audio: Annotated[UploadFile | None, File()] = None,
    mock: bool = False,
):
    if mock:
        return _mock("onboarding_turn.json")
    parsed, err = _parse_json(session, Session, "session")
    if err:
        return err
    data, mime = _read_audio(audio)
    try:
        return run_onboarding_turn(parsed, data, mime)
    except GeminiError as e:
        return _error(502, str(e), e.retryable)
    except Exception as e:  # noqa: BLE001  (never crash the flow)
        log.error("onboarding_turn failed: %s", type(e).__name__)
        return _error(500, "Something went wrong. Please try again.", True)


@router.post("/voice/answer")
def voice_answer(
    session: Annotated[str, Form()],
    field: Annotated[str | None, Form()] = None,
    audio: Annotated[UploadFile | None, File()] = None,
    question: Annotated[str | None, Form()] = None,
    mock: bool = False,
):
    if mock:
        return _mock("voice_answer.json")
    sess, err = _parse_json(session, Session, "session")
    if err:
        return err
    if not field:
        return _error(422, "field is required", False)
    gap_field, err = _parse_json(field, GapField, "field")
    if err:
        return err
    parsed = VoiceAnswerState(
        language=sess.language,
        form_id=sess.selected_form,
        field=gap_field,
        question=question or None,
    )
    data, mime = _read_audio(audio)
    if not data:
        return _error(400, "No audio received", False)
    try:
        return parse_voice_answer(parsed, data, mime)
    except GeminiError as e:
        return _error(502, str(e), e.retryable)
    except Exception as e:  # noqa: BLE001  (never crash the flow)
        log.error("voice_answer failed: %s", type(e).__name__)
        return _error(500, "Something went wrong. Please try again.", True)
