"""One onboarding turn: user's audio + current profile → merged profile + next question.

Two Gemini calls per turn: (1) plain transcription of the audio, (2) extraction +
next question from that text. One combined audio call misheard numbers and dates.
"""

from __future__ import annotations

import re
import unicodedata

from .client import call_audio_json
from .profile_fields import (
    ONBOARDING_FIELDS,
    coerce_members,
    coerce_value,
    merge_updates,
    remaining_fields,
)
from .prompts import (
    TRANSCRIBE_SYSTEM,
    onboarding_prompt,
    onboarding_system,
    transcribe_prompt,
)
from .schemas import (
    Intent,
    OnboardingExtraction,
    OnboardingTurnResponse,
    Session,
    Transcription,
)

SOURCE = "onboarding_voice"
_NO_UPDATE_INTENTS = {Intent.unclear, Intent.question, Intent.off_topic}
# An optional free-text answer meaning "nothing" is a skip, not a value.
_NONE_ANSWERS = {
    "no",
    "none",
    "null",
    "nothing",
    "nada",
    "ninguno",
    "ninguna",
    "no aplica",
    "n/a",
}
# Names not spelled out letter by letter must be confirmed in the recap (CLAUDE.md).
UNSPELLED_NAME_MAX_CONFIDENCE = 0.7


def _letters(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if c.isalpha() and not unicodedata.combining(c)).lower()


def spelled_out(name: str, transcript: str) -> bool:
    """True if the transcript spells the name letter by letter ("L-O-P-E-Z", "L, O, P, E, Z")."""
    letters = _letters(name)
    if len(letters) < 2:
        return False
    pattern = r"(?<![a-z])" + r"[\s,.\-]+".join(letters) + r"(?![a-z])"
    text = unicodedata.normalize("NFKD", transcript.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.search(pattern, text) is not None


def run_onboarding_turn(
    session: Session, audio: bytes | None, mime_type: str | None
) -> OnboardingTurnResponse:
    has_audio = bool(audio)
    profile = session.profile or {}
    skipped = set(session.skipped)

    transcript = None
    if has_audio:
        heard: Transcription = call_audio_json(
            audio=audio,
            mime_type=mime_type,
            system_instruction=TRANSCRIBE_SYSTEM,
            prompt=transcribe_prompt(session.last_question, session.language),
            schema=Transcription,
        )
        transcript = heard.transcript.strip()

    ext: OnboardingExtraction = call_audio_json(
        audio=None,
        mime_type=None,
        system_instruction=onboarding_system(session.language),
        prompt=onboarding_prompt(
            profile=profile,
            remaining=remaining_fields(profile, skipped),
            last_question=session.last_question,
            transcript=transcript,
        ),
        schema=OnboardingExtraction,
    )
    if transcript is not None:
        ext.transcript = transcript  # the plain transcription, not Gemini's echo of it
    return apply_extraction(session, ext, has_audio)


def apply_extraction(
    session: Session, ext: OnboardingExtraction, has_audio: bool
) -> OnboardingTurnResponse:
    """Pure merge step (no Gemini) so it can be unit-tested."""
    profile = session.profile or {}
    skipped = set(session.skipped)
    updated_keys: list[str] = []
    rejected: list[str] = []

    if has_audio and ext.intent not in _NO_UPDATE_INTENTS:
        typed = []
        for u in ext.updates:
            key = u.key.value
            spec = ONBOARDING_FIELDS[key]
            if (
                spec.optional
                and spec.type == "string"
                and str(u.value).strip(" .!").lower() in _NONE_ANSWERS
            ):
                skipped.add(key)
                continue
            value = coerce_value(spec.type, u.value, spec.options)
            if value is None:
                rejected.append(key)
                continue
            confidence = u.confidence
            if spec.type == "name" and not spelled_out(str(value), ext.transcript):
                confidence = min(confidence, UNSPELLED_NAME_MAX_CONFIDENCE)
            typed.append({"key": key, "value": value, "confidence": confidence})

        if ext.household_members is not None:
            members = coerce_members(ext.household_members)
            current = profile.get("household_members") or {}
            if members != current.get(
                "value"
            ):  # Gemini often re-sends an unchanged list
                typed.append(
                    {
                        "key": "household_members",
                        "value": members,
                        "confidence": ext.household_members_confidence or 0.8,
                    }
                )

        is_correction = ext.intent == Intent.correction
        profile, updated_keys = merge_updates(
            profile,
            [t for t in typed if t["key"] != "household_members"],
            SOURCE,
            overwrite=is_correction,
        )
        # The member list is always a full replacement of the previous list.
        members = [t for t in typed if t["key"] == "household_members"]
        if members:
            profile, more = merge_updates(profile, members, SOURCE, overwrite=True)
            updated_keys += more
        skipped |= {k.value for k in ext.skipped_keys}

    # A field that now has a value is no longer skipped (e.g. user came back and answered).
    skipped = {
        k
        for k in skipped
        if not (
            isinstance(profile.get(k), dict) and profile[k].get("value") is not None
        )
    }
    remaining = remaining_fields(profile, skipped)

    return OnboardingTurnResponse(
        transcript=ext.transcript if has_audio else "",
        intent=ext.intent.value,
        profile=profile,
        skipped=sorted(skipped),
        updated_keys=updated_keys,
        rejected_keys=rejected,
        next_question=ext.next_question,
        done=not remaining,
        remaining=remaining,
    )
