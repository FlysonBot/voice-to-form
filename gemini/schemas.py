"""Pydantic models.

Two kinds:
- *Gemini response schemas* (passed as `response_schema`). Keep them Gemini-friendly:
  no free-form dicts, no Union of types, no default values. Values are strings; the
  backend coerces types in profile_fields.coerce_value().
- *API request/response models* for the routes in routers/audio.py.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from .profile_fields import EXTRACTABLE_KEYS, RELATIONSHIPS

# ---------- Gemini response schemas ----------

# Enum built from the catalog so Gemini can only return keys we know.
ProfileKey = Enum("ProfileKey", {k: k for k in EXTRACTABLE_KEYS}, type=str)
Relationship = Enum("Relationship", {r: r for r in RELATIONSHIPS}, type=str)


class Intent(str, Enum):
    answer = "answer"
    skip = "skip"
    correction = "correction"
    unclear = "unclear"
    question = "question"
    off_topic = "off_topic"


class FieldUpdate(BaseModel):
    key: ProfileKey
    value: str
    confidence: float


class HouseholdMember(BaseModel):
    first_name: str | None
    relationship: Relationship
    date_of_birth: str | None


class OnboardingExtraction(BaseModel):
    transcript: str
    intent: Intent
    updates: list[FieldUpdate]
    household_members: list[HouseholdMember] | None
    household_members_confidence: float | None
    skipped_keys: list[ProfileKey]
    next_question: str


class AnswerStatus(str, Enum):
    answered = "answered"
    skipped = "skipped"
    leave_blank = "leave_blank"
    unclear = "unclear"


class VoiceAnswerExtraction(BaseModel):
    transcript: str
    status: AnswerStatus
    value: str | None
    confidence: float
    retry_question: str


class Transcription(BaseModel):
    transcript: str
    language_detected: str


# ---------- API models ----------


class Session(BaseModel):
    """The shared data format from CLAUDE.md, sent by the client on every call.

    Only the keys used here are declared; other keys (suggested_programs,
    signature_png, ...) are accepted and ignored. `skipped` and `last_question` are
    extra session keys that onboarding needs.
    """

    language: str = "es"
    profile: dict[str, Any] = Field(default_factory=dict)
    selected_form: str | None = None
    skipped: list[str] = Field(default_factory=list)
    last_question: str | None = None


class OnboardingTurnResponse(BaseModel):
    transcript: str
    intent: str
    profile: dict[str, Any]
    skipped: list[str]
    updated_keys: list[str]
    rejected_keys: list[
        str
    ]  # Gemini returned a value we couldn't use (bad date, 9-digit phone...)
    next_question: str
    done: bool
    remaining: list[str]


class GapField(BaseModel):
    key: str
    label_en: str
    type: str = "string"  # string|name|digits|date|number|int|phone|zip|email|enum|bool
    options: list[str] | None = None
    description_en: str | None = None
    sensitive: bool = (
        False  # SSN, account numbers: confidence capped so recap reads it back
    )


class VoiceAnswerState(BaseModel):
    """Internal input for parse_voice_answer(), built from the request's session + field."""

    language: str = "es"
    form_id: str | None = None
    field: GapField
    question: str | None = None  # the question that was spoken, if known


class VoiceAnswerResponse(BaseModel):
    field_key: str
    transcript: str
    status: str
    value: Any
    confidence: float
    source: str = "gap_voice"
    clarification_question: str | None  # set when status == "unclear"
