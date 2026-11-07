"""Glue between the frontend's API calls and each owner's backend code.

Each role folder keeps its own contract (API.md). Where the frontend (P4) sends or
expects a slightly different shape, these routes translate and then call the owner's
functions unchanged:

  POST /onboarding/turn  frontend: multipart audio?, text?, session, history
                         -> gemini.run_onboarding_turn (P2); adds `reply`, keeps skips
  POST /voice/answer     frontend: multipart audio?, text?, field (a profile KEY), session
                         -> gemini.parse_voice_answer (P2) with a GapField built here
  POST /form/gaps        nobody had built it: required "gap" fields from P1's
                         form_engine/<form_id>.fields.json that the profile lacks

Skipped / "leave it blank" answers are stored as {"value": ""} in the profile: that is
the frontend's convention for "left blank, fill in by hand" (P1 leaves those empty).
Never log values: only error types.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from gemini.client import GeminiError, call_audio_json
from gemini.onboarding import apply_extraction, run_onboarding_turn
from gemini.profile_fields import ONBOARDING_FIELDS, remaining_fields
from gemini.prompts import onboarding_prompt, onboarding_system
from gemini.schemas import GapField, OnboardingExtraction, Session, VoiceAnswerState
from gemini.voice_answer import parse_voice_answer

log = logging.getLogger("server.adapters")
router = APIRouter()

ROOT = Path(__file__).resolve().parent.parent
GEMINI_MOCKS = ROOT / "gemini" / "mocks"
FORM_DIR = ROOT / "form_engine"
FORM_NAMES = {"sdge_care": "SDG&E CARE"}

# GapField types P2's answer parser understands.
_GAP_TYPES = {"string", "name", "digits", "date", "number", "int", "phone", "zip", "email", "enum", "bool"}
# Extra hints for gap-only keys (types are not in P1's fields.json).
_GAP_HINTS = {
    "sdge_account_number": dict(type="digits", sensitive=True,
                                description_en="SDG&E account number, printed at the top of the energy bill"),
    "home_phone": dict(type="phone", description_en="home landline phone number, if different from the mobile"),
    "ssn": dict(type="digits", sensitive=True, description_en="Social Security number"),
}


def _error(status: int, message: str, retryable: bool) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": message, "retryable": retryable})


def _form_fields(form_id: str) -> list[dict]:
    path = FORM_DIR / f"{form_id}.fields.json"
    if not path.is_file():
        return []
    return json.loads(path.read_text(encoding="utf-8")).get("fields", [])


def _label(key: str, form_id: str | None) -> str:
    for f in _form_fields(form_id or "sdge_care"):
        if f.get("profile_key") == key and f.get("label"):
            return f["label"]
    return key.replace("_", " ").capitalize()


def gap_field(key: str, form_id: str | None = None) -> GapField:
    """Build P2's GapField from a bare profile key (what the frontend sends)."""
    spec = ONBOARDING_FIELDS.get(key)
    hint = dict(_GAP_HINTS.get(key, {}))
    if spec is not None:
        hint.setdefault("type", spec.type if spec.type in _GAP_TYPES else "string")
        hint.setdefault("description_en", spec.description)
        if spec.options:
            hint.setdefault("options", list(spec.options))
    return GapField(key=key, label_en=_label(key, form_id), **hint)


def describe(key: str, form_id: str | None = None) -> str:
    f = gap_field(key, form_id)
    return f.description_en or f.label_en


def form_name(form_id: str | None) -> str:
    return FORM_NAMES.get(form_id or "", form_id or "")


# ---------- skipped fields <-> {"value": ""} ----------
def _split_skipped(profile: dict) -> tuple[dict, list[str]]:
    clean, skipped = {}, []
    for k, e in (profile or {}).items():
        if isinstance(e, dict) and e.get("value") == "":
            skipped.append(k)
        else:
            clean[k] = e
    return clean, skipped


def _blank(source: str) -> dict:
    return {"value": "", "confidence": 1.0, "source": source}


def _last_assistant(history: str | None) -> str | None:
    try:
        msgs = json.loads(history) if history else []
        for m in reversed(msgs):
            if m.get("role") == "assistant" and m.get("text"):
                return m["text"]
    except (ValueError, AttributeError, TypeError):
        pass
    return None


def _maybe_tts(text: str) -> dict:
    """Optional Gemini voice (USE_GEMINI_TTS=1). Any failure -> no audio; the browser speaks."""
    if os.environ.get("USE_GEMINI_TTS") != "1" or not text:
        return {}
    try:
        from voice.tts import synthesize

        return {"audio_b64": synthesize(text), "audio_mime": "audio/wav"}
    except Exception as e:  # noqa: BLE001
        log.warning("TTS failed: %s", type(e).__name__)
        return {}


# ---------- POST /onboarding/turn ----------
def _onboarding_from_text(session: Session, text: str):
    """Typed answer ("Type instead"): same as P2's turn, with the text as the transcript."""
    ext: OnboardingExtraction = call_audio_json(
        audio=None,
        mime_type=None,
        system_instruction=onboarding_system(session.language),
        prompt=onboarding_prompt(
            profile=session.profile,
            remaining=remaining_fields(session.profile, set(session.skipped)),
            last_question=session.last_question,
            transcript=text,
        ),
        schema=OnboardingExtraction,
    )
    ext.transcript = text
    return apply_extraction(session, ext, True)


@router.post("/onboarding/turn")
def onboarding_turn(
    session: Annotated[str, Form()],
    audio: Annotated[UploadFile | None, File()] = None,
    text: Annotated[str | None, Form()] = None,
    history: Annotated[str | None, Form()] = None,
    mock: bool = False,
):
    if mock:
        out = json.loads((GEMINI_MOCKS / "onboarding_turn.json").read_text(encoding="utf-8"))
        return {**out, "reply": out.get("next_question", "")}
    try:
        raw = json.loads(session)
    except ValueError:
        return _error(422, "session is not valid JSON", False)
    profile, skipped = _split_skipped(raw.get("profile") or {})
    sess = Session(
        language=raw.get("language") or "es",
        profile=profile,
        selected_form=raw.get("selected_form"),
        skipped=sorted(set(skipped) | set(raw.get("skipped") or [])),
        last_question=raw.get("last_question") or _last_assistant(history),
    )
    data = audio.file.read() if audio is not None else None
    try:
        if data:
            out = run_onboarding_turn(sess, data, audio.content_type)
        elif text and text.strip():
            out = _onboarding_from_text(sess, text.strip())
        else:
            out = run_onboarding_turn(sess, None, None)  # first turn: greeting
    except GeminiError as e:
        return _error(502, str(e), e.retryable)
    except Exception as e:  # noqa: BLE001  (never crash the flow)
        log.error("onboarding_turn failed: %s", type(e).__name__)
        return _error(500, "Something went wrong. Please try again.", True)

    res = out.model_dump()
    res["profile"] = {**res["profile"], **{k: _blank("onboarding_voice") for k in res["skipped"]
                                           if k not in res["profile"]}}
    res["reply"] = res["next_question"]
    return {**res, **_maybe_tts(res["reply"])}


# ---------- POST /voice/answer ----------
@router.post("/voice/answer")
def voice_answer(
    session: Annotated[str, Form()],
    field: Annotated[str, Form()],
    audio: Annotated[UploadFile | None, File()] = None,
    text: Annotated[str | None, Form()] = None,
    question: Annotated[str | None, Form()] = None,
    mock: bool = False,
):
    if mock:
        return json.loads((GEMINI_MOCKS / "voice_answer.json").read_text(encoding="utf-8"))
    try:
        raw = json.loads(session)
    except ValueError:
        return _error(422, "session is not valid JSON", False)
    form_id = raw.get("selected_form")
    try:
        gf = GapField.model_validate(json.loads(field))  # P2's shape: a JSON object
    except (ValueError, TypeError):
        gf = gap_field(field.strip(), form_id)  # frontend's shape: a bare key
    if gf.key == "household_members":
        return _error(422, "Household members can't be changed here yet. Please fix them on the paper form.", False)

    data = audio.file.read() if audio is not None else None
    if not data:
        if text and text.strip():  # typed answer: exact, no Gemini needed
            return {"field_key": gf.key, "transcript": text.strip(), "status": "answered",
                    "value": text.strip(), "confidence": 1.0, "source": "gap_voice",
                    "clarification_question": None}
        return _error(400, "No audio received", False)

    state = VoiceAnswerState(language=raw.get("language") or "es", form_id=form_id, field=gf,
                             question=question or None)
    try:
        res = parse_voice_answer(state, data, audio.content_type).model_dump()
    except GeminiError as e:
        return _error(502, str(e), e.retryable)
    except Exception as e:  # noqa: BLE001
        log.error("voice_answer failed: %s", type(e).__name__)
        return _error(500, "Something went wrong. Please try again.", True)
    if res["status"] in ("skipped", "leave_blank"):
        res["value"], res["confidence"] = "", 1.0  # frontend: "left blank, fill in by hand"
    return res


# ---------- POST /form/gaps ----------
class GapsIn(BaseModel):
    session: dict[str, Any] = {}
    form_id: str = "sdge_care"


@router.post("/form/gaps")
def form_gaps(body: GapsIn, mock: bool = False):
    if mock:
        return {"missing_fields": ["sdge_account_number"]}
    profile = body.session.get("profile") or {}
    missing = []
    for f in _form_fields(body.form_id):
        key = f.get("profile_key")
        if f.get("source") != "gap" or not f.get("required") or not key:
            continue
        entry = profile.get(key)
        value = entry.get("value") if isinstance(entry, dict) else entry
        if value is None:  # "" means the user chose to leave it blank: don't re-ask
            missing.append(key)
    return {"missing_fields": missing}


# ---------- POST /voice/question (P3 voice) ----------
class QuestionIn(BaseModel):
    session: dict[str, Any] = {}
    field: str
    language: str | None = None
    retry_reason: str = ""


@router.post("/voice/question")
def voice_question(body: QuestionIn, mock: bool = False):
    from voice import mocks
    from voice.gaps_recap import make_question

    if mock:
        r = mocks.question(body.field)
        return {**r, "text": r["question"]}
    form_id = body.session.get("selected_form")
    language = body.language or body.session.get("language") or "es"
    try:
        r = make_question(language, body.field, describe(body.field, form_id), form_name(form_id), body.retry_reason)
    except ValueError as e:  # immigration / citizenship: never asked
        return _error(400, str(e), False)
    except GeminiError as e:
        return _error(502, str(e), e.retryable)
    except Exception as e:  # noqa: BLE001
        log.error("voice_question failed: %s", type(e).__name__)
        return _error(502, "Question failed. Please try again.", True)
    return {**r, "text": r["question"], **_maybe_tts(r["question"])}


# ---------- POST /recap (P3 voice) ----------
class RecapIn(BaseModel):
    session: dict[str, Any] = {}


@router.post("/recap")
def recap(body: RecapIn, mock: bool = False):
    from voice import mocks
    from voice.gaps_recap import make_recap

    profile = body.session.get("profile") or {}
    blank = [k for k, e in profile.items() if isinstance(e, dict) and e.get("value") == ""]
    try:
        if mock:
            r = mocks.recap(profile)
        else:
            r = make_recap(body.session.get("language") or "es", profile,
                           form_name(body.session.get("selected_form")), blank)
    except Exception as e:  # noqa: BLE001
        log.error("recap failed: %s", type(e).__name__)
        return _error(502, "Recap failed. Please try again.", True)
    r["text"] = r["script"]
    for it in r["items"]:
        it["needs_confirm"] = it["low_confidence"]
    return {**r, **({} if mock else _maybe_tts(r["script"]))}
