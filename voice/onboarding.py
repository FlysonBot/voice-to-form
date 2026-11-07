"""Voice onboarding loop: one turn = user's audio + current profile -> updated profile + next question.

The model extracts whatever the answer contains (one answer can fill several
fields), and writes the next question in the user's language. Python decides
when we're done (every field filled or skipped), not the model.
"""
import json

from pydantic import BaseModel

from .fields import (
    FIELD_DESC,
    FIELD_KEYS,
    LANGUAGES,
    ONBOARDING_FIELDS,
    add_derived,
    coerce,
    is_filled,
    remaining_fields,
    value_of,
)
from .gemini_client import audio_part, structured_call


class Extracted(BaseModel):
    field: str
    value: str
    confidence: float


class Member(BaseModel):
    first_name: str
    relationship: str
    date_of_birth: str  # YYYY-MM-DD or "" if unknown


class TurnOut(BaseModel):
    transcript: str                 # what the user said, in their language
    extracted: list[Extracted]
    skipped_fields: list[str]       # fields the user explicitly skipped
    household_members: list[Member] # other people in the home; [] if not mentioned this turn
    wants_correction: bool          # user said something was wrong ("no, that's wrong")
    correction_field: str           # which field they want to fix, "" if unclear
    next_question: str              # in the user's language; one short question
    closing_message: str            # in the user's language; used only if everything is done
    spoken_language: str            # code of the language the user SPOKE this turn, or "" (see LANGUAGE rules)


SYSTEM = """You are a warm, patient assistant helping a person in San Diego build a profile so we can fill government benefit forms for them.
You are talking with them by VOICE. Current language: {lang}. Many users have little formal education or are not confident with paperwork. Use short, simple, friendly sentences.

LANGUAGE
- Supported languages (code: name): {codes}
- spoken_language: the code of the language the user actually spoke this turn, ONLY if their answer contains a phrase or sentence clearly in one supported language. Return "" if there was no speech, or the answer is just a name, a number, an address, "yes"/"no" or "ok" (those don't reveal the language), or the language isn't supported.
- Write next_question and closing_message in the language of spoken_language if it is not "", otherwise in {lang}. Never mix languages, except in the greeting rule below.
{auto_rule}
RULES
- Field VALUES must be in English / Latin letters, as US forms require (transliterate names; numbers as digits; dates YYYY-MM-DD; money as plain numbers in USD).
- Extract EVERY field the answer contains, even fields you didn't ask about. Example: "it's me, my husband and two kids" -> household_size=4 and household_members.
- household_members = the OTHER people (not the user). If they live alone: household_size=1, household_members empty.
- Benefits are yes/no per program: ask "Do you already get CalFresh, Medi-Cal, WIC, SSI or free school meals?" once; "only Medi-Cal" -> benefits_medi_cal=true and the other benefits_* = false.
- confidence: 0.0-1.0. Use < 0.8 if audio was unclear, a name spelling is uncertain, or a value is a guess/range.
- If the user says "skip", "I don't know" or similar to an OPTIONAL field, put it in skipped_fields. Required fields cannot be skipped: gently explain it's needed and ask again more simply.
- Never ask about immigration status, citizenship, SSN, bank details or utility account numbers.
- next_question: ask about the NEXT unfilled field(s) after applying what you just extracted, ONE short question at a time, conversational ("Who lives with you?"), not a checklist. You may group tightly related things (street + unit). Briefly acknowledge the answer first (a few words).
- For names, after hearing them, confirm the spelling letter by letter in the next question if unsure.
- If the user says something is wrong, set wants_correction=true, correction_field, and ask for the right value.
- Only use field names from this list: {fields}
"""


def _fields_brief(profile: dict) -> str:
    lines = []
    for k in FIELD_KEYS:
        entry = profile.get(k)
        if isinstance(entry, dict) and entry.get("skipped"):
            state = "SKIPPED"
        elif is_filled(profile, k):
            state = f"FILLED: {json.dumps(value_of(profile, k), ensure_ascii=False)}"
        else:
            state = "MISSING"
        lines.append(f"- {k} ({FIELD_DESC[k]}): {state}")
    return "\n".join(lines)


def _merge(profile: dict, out: TurnOut) -> dict:
    profile = dict(profile)
    for ex in out.extracted:
        if ex.field not in FIELD_KEYS or ex.field == "household_members":
            continue
        value = coerce(ex.field, ex.value)
        if value is None:
            continue
        profile[ex.field] = {"value": value, "confidence": round(ex.confidence, 2), "source": "onboarding_voice"}
    for f in out.skipped_fields:
        if f in FIELD_KEYS:
            profile[f] = {"value": None, "confidence": 1.0, "source": "onboarding_voice", "skipped": True}
    if out.household_members:
        # Plain list, per CLAUDE.md: profile.household_members = [{first_name, relationship, date_of_birth}]
        profile["household_members"] = [m.model_dump() for m in out.household_members]
        if value_of(profile, "household_size") is None:
            profile["household_size"] = {"value": len(profile["household_members"]) + 1, "confidence": 0.8,
                                         "source": "onboarding_voice"}
    elif value_of(profile, "household_size") == 1 and not isinstance(profile.get("household_members"), list):
        profile["household_members"] = []  # lives alone
    if out.wants_correction and out.correction_field in FIELD_KEYS and not any(
        e.field == out.correction_field for e in out.extracted
    ):
        profile.pop(out.correction_field, None)  # clear it so it gets re-asked
    return add_derived(profile)


def onboarding_turn(language: str, profile: dict, audio_b64: str | None, mime_type: str,
                    last_question: str, user_text: str | None = None) -> dict:
    auto = language not in LANGUAGES  # "auto" (or unknown): detect from the user's speech
    lang = "not chosen yet (auto-detect)" if auto else LANGUAGES[language]
    auto_rule = (
        "- AUTO MODE: the user has not chosen a language. If you can't tell the language yet (e.g. the very first turn), "
        "write next_question as ONE short greeting + question in English, then the same in Spanish, and invite them to answer in any language.\n"
        if auto else ""
    )
    system = SYSTEM.format(lang=lang, auto_rule=auto_rule, fields=", ".join(FIELD_KEYS),
                           codes=", ".join(f"{k}: {v}" for k, v in LANGUAGES.items()))
    optional = [k for k, _, opt, _ in ONBOARDING_FIELDS if opt]

    context = (
        f"Optional fields (can be skipped): {', '.join(optional)}\n\n"
        f"Current profile state:\n{_fields_brief(profile)}\n\n"
        f"The question you last asked: {last_question or '(none — this is the start; greet them briefly, say we do not store their information, and ask the first question)'}"
    )
    contents = [context]
    if audio_b64:
        contents.append("The user's spoken answer is attached.")
        contents.append(audio_part(audio_b64, mime_type))
    elif user_text:
        # From a button, e.g. "skip" or "I scanned a document; continue with what's still missing."
        contents.append(f"The user pressed a button meaning: {user_text}")
    else:
        contents.append("No audio this turn. extracted/skipped_fields/household_members must be empty, transcript empty.")

    out: TurnOut = structured_call(contents, TurnOut, system)

    # Switch language only on a supported language Gemini heard clearly in actual speech.
    heard = out.spoken_language.strip().lower() if audio_b64 else ""
    new_language = heard if heard in LANGUAGES else language

    # Drop "skips" of required fields — the model is told not to, but enforce it.
    out.skipped_fields = [f for f in out.skipped_fields if f in optional]
    new_profile = _merge(profile, out)
    remaining = remaining_fields(new_profile)
    done = len(remaining) == 0
    return {
        "profile": new_profile,
        "transcript": out.transcript,
        "say": out.closing_message if done else out.next_question,
        "done": done,
        "remaining_fields": remaining,
        "updated_fields": [e.field for e in out.extracted if e.field in new_profile]
        + (["household_members"] if out.household_members else []),
        "language": new_language,          # "auto" until a language is detected
        "language_changed": new_language != language,
    }
