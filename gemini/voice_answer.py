"""Gap filling: user's audio + one form-specific field → typed value."""

from __future__ import annotations

from .client import call_audio_json
from .profile_fields import coerce_value
from .prompts import (
    NUMBER_FIELD_TYPES,
    number_answer_prompt,
    number_answer_system,
    voice_answer_prompt,
    voice_answer_system,
)
from .schemas import (
    AnswerStatus,
    VoiceAnswerExtraction,
    VoiceAnswerResponse,
    VoiceAnswerState,
)

# Sensitive values (SSN, account numbers) land just under the recap threshold (0.8),
# so the user always has to confirm them explicitly.
SENSITIVE_MAX_CONFIDENCE = 0.79


def parse_voice_answer(
    state: VoiceAnswerState, audio: bytes, mime_type: str | None
) -> VoiceAnswerResponse:
    field = state.field.model_dump()
    if state.field.type in NUMBER_FIELD_TYPES:
        system = number_answer_system(state.language)
        prompt = number_answer_prompt(field=field)
    else:
        system = voice_answer_system(state.language)
        prompt = voice_answer_prompt(
            field=field, question=state.question, form_id=state.form_id
        )
    ext: VoiceAnswerExtraction = call_audio_json(
        audio=audio,
        mime_type=mime_type,
        system_instruction=system,
        prompt=prompt,
        schema=VoiceAnswerExtraction,
    )
    return apply_answer(state, ext)


def apply_answer(
    state: VoiceAnswerState, ext: VoiceAnswerExtraction
) -> VoiceAnswerResponse:
    """Pure step (no Gemini) so it can be unit-tested."""
    f = state.field
    status = ext.status
    value = None
    confidence = 0.0

    if status == AnswerStatus.answered:
        value = coerce_value(f.type, ext.value, f.options)
        if value is None:
            status = AnswerStatus.unclear
        else:
            confidence = max(0.0, min(1.0, ext.confidence))
            if f.sensitive:
                confidence = min(confidence, SENSITIVE_MAX_CONFIDENCE)

    return VoiceAnswerResponse(
        field_key=f.key,
        transcript=ext.transcript,
        status=status.value,
        value=value,
        confidence=round(confidence, 2),
        clarification_question=ext.retry_question
        if status == AnswerStatus.unclear
        else None,
    )
