"""FastAPI routes for voice & language. Mount in main.py:

    from voice.router import router as voice_router
    app.include_router(voice_router)

Every route supports ?mock=true so the frontend works without a Gemini key.
Audio comes in as base64 WAV (16 kHz mono) — the frontend recorder converts it.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from . import mocks
from .gaps_recap import make_question, make_recap, parse_answer, recap_correct
from .gemini_client import ConfigError
from .onboarding import onboarding_turn
from .tts import synthesize

router = APIRouter()


def _fail(what: str, e: Exception):
    if isinstance(e, ConfigError):  # setup problem, safe to show (names the env var only)
        print(f"[voice] {what} failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    # Log only the error type — never the payload (it may contain personal info).
    print(f"[voice] {what} failed: {type(e).__name__}")
    raise HTTPException(status_code=502, detail=f"{what} failed. Please try again.")


# ---------- request bodies ----------
class OnboardingTurnIn(BaseModel):
    language: str = "es"
    profile: dict = {}
    audio_b64: str | None = None  # None on the very first turn
    mime_type: str = "audio/wav"
    last_question: str = ""
    user_text: str | None = None  # button input: "skip", "scanned a document", ...


class QuestionIn(BaseModel):
    language: str = "es"
    field: str
    description: str = ""
    form_name: str = ""
    retry_reason: str = ""
    with_audio: bool = False  # CLAUDE.md: "question text (+ audio)"


class AnswerIn(BaseModel):
    language: str = "es"
    field: str
    description: str = ""
    question: str = ""
    audio_b64: str
    mime_type: str = "audio/wav"


class RecapIn(BaseModel):
    language: str = "es"
    profile: dict
    form_name: str = ""
    blank_fields: list[str] = []
    with_audio: bool = False  # CLAUDE.md: "recap text (+ audio)"


class RecapCorrectIn(BaseModel):
    language: str = "es"
    profile: dict
    audio_b64: str
    mime_type: str = "audio/wav"
    current_field: str = ""


class TTSIn(BaseModel):
    text: str
    language: str = "es"


def _with_audio(result: dict, text: str, wanted: bool) -> dict:
    """Optionally attach TTS. A TTS failure never fails the request: audio_b64 = None
    and the frontend falls back to speechSynthesis."""
    if not wanted:
        return result
    try:
        result["audio_b64"], result["audio_mime_type"] = synthesize(text), "audio/wav"
    except Exception as e:
        print(f"[voice] TTS failed: {type(e).__name__}")
        result["audio_b64"], result["audio_mime_type"] = None, None
    return result


# ---------- routes ----------
@router.post("/onboarding/turn")
def post_onboarding_turn(body: OnboardingTurnIn, mock: bool = Query(False)):
    if mock:
        return mocks.onboarding_turn(body.profile, body.audio_b64 is not None or body.user_text is not None)
    try:
        return onboarding_turn(body.language, body.profile, body.audio_b64, body.mime_type, body.last_question,
                               body.user_text)
    except Exception as e:
        _fail("Onboarding turn", e)


@router.post("/voice/question")
def post_voice_question(body: QuestionIn, mock: bool = Query(False)):
    if mock:
        return mocks.question(body.field)
    try:
        r = make_question(body.language, body.field, body.description, body.form_name, body.retry_reason)
        return _with_audio(r, r["question"], body.with_audio)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        _fail("Question", e)


@router.post("/voice/answer")
def post_voice_answer(body: AnswerIn, mock: bool = Query(False)):
    if mock:
        return mocks.answer(body.field)
    try:
        return parse_answer(body.language, body.field, body.description, body.question, body.audio_b64, body.mime_type)
    except Exception as e:
        _fail("Answer parsing", e)


@router.post("/recap")
def post_recap(body: RecapIn, mock: bool = Query(False)):
    if mock:
        return mocks.recap(body.profile)
    try:
        r = make_recap(body.language, body.profile, body.form_name, body.blank_fields)
        return _with_audio(r, r["script"], body.with_audio)
    except Exception as e:
        _fail("Recap", e)


@router.post("/recap/correct")
def post_recap_correct(body: RecapCorrectIn, mock: bool = Query(False)):
    if mock:
        return mocks.correct(body.profile)
    try:
        return recap_correct(body.language, body.profile, body.audio_b64, body.mime_type, body.current_field)
    except Exception as e:
        _fail("Correction", e)


@router.post("/voice/tts")
def post_tts(body: TTSIn, mock: bool = Query(False)):
    # Mock returns no audio -> frontend uses browser speechSynthesis.
    if mock:
        return {"audio_b64": None, "mime_type": None}
    try:
        return {"audio_b64": synthesize(body.text), "mime_type": "audio/wav"}
    except Exception as e:
        _fail("Speech", e)
