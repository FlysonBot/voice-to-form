"""Form-specific gap questions, spoken-answer parsing, recap and recap corrections."""
import json
from typing import Literal

from pydantic import BaseModel

from .fields import (
    DERIVED,
    FIELD_TYPES,
    LANGUAGES,
    NEVER_ASK,
    SENSITIVE_GAP_FIELDS,
    add_derived,
    coerce,
)
from .gemini_client import audio_part, structured_call

STYLE = """You talk with the user by VOICE in {lang}. Use short, simple, warm sentences — many users are not confident with paperwork.
Everything you SAY to the user must be in {lang}. Field VALUES stay in English / Latin letters as US forms require
(digits for numbers, YYYY-MM-DD for dates, plain USD numbers for money)."""


# ---------- /voice/question ----------
class QuestionOut(BaseModel):
    question: str


def make_question(language: str, field: str, description: str, form_name: str, retry_reason: str = "") -> dict:
    lang = LANGUAGES.get(language, "English")
    if field.lower() in NEVER_ASK:
        raise ValueError("This field is never asked by the app (immigration/citizenship).")
    sensitive = field.lower() in SENSITIVE_GAP_FIELDS
    prompt = (
        f"Form: {form_name or 'a benefits form'}\nField to ask for: {field}\nWhat it means: {description or field}\n"
        + (f"We are asking again because: {retry_reason}. Ask more simply, maybe with an example.\n" if retry_reason else "")
        + ("This is sensitive. Tell them they can say 'leave it blank' and write it on the paper form themselves.\n" if sensitive else "")
        + "Write ONE short spoken question. If they might not know where to find it (e.g. an account number), say where it usually is (e.g. top of the bill)."
    )
    out: QuestionOut = structured_call(prompt, QuestionOut, STYLE.format(lang=lang), temperature=0.4)
    return {"field": field, "question": out.question}


# ---------- /voice/answer ----------
class AnswerOut(BaseModel):
    transcript: str
    intent: Literal["answer", "skip", "leave_blank", "repeat", "unclear", "wrong"]
    value: str        # English/Latin, normalized; "" unless intent == answer
    confidence: float
    reply: str        # spoken back in the user's language


ANSWER_RULES = """Classify the spoken answer:
- answer: they gave a value. Normalize it (spoken digits -> "1234 5678 90", "five hundred" -> "500").
- skip / leave_blank: they don't know, don't have it, or want to write it themselves.
- repeat: they asked to hear the question again.
- wrong: they say a previous answer was wrong / want to change it.
- unclear: you can't understand or it doesn't answer the question.
reply: if answer -> confirm what you heard briefly (read numbers back digit by digit) so they can object;
if leave_blank -> say that's fine and they can write it on the paper form; if unclear -> politely ask again more simply;
if repeat -> repeat the question. confidence < 0.8 if audio was unclear or you guessed."""


def parse_answer(language: str, field: str, description: str, question: str, audio_b64: str, mime_type: str) -> dict:
    lang = LANGUAGES.get(language, "English")
    prompt = f"We asked for field `{field}` ({description or field}).\nQuestion we asked: {question}\n\n{ANSWER_RULES}"
    out: AnswerOut = structured_call([prompt, audio_part(audio_b64, mime_type)], AnswerOut, STYLE.format(lang=lang))
    result = out.model_dump()
    if out.intent == "answer" and out.value:
        result["profile_entry"] = {"value": out.value, "confidence": round(out.confidence, 2), "source": "gap_voice"}
    elif out.intent in ("skip", "leave_blank"):
        result["profile_entry"] = {"value": None, "confidence": 1.0, "source": "gap_voice", "skipped": True}
    else:
        result["profile_entry"] = None
    return result


# ---------- /recap ----------
class RecapItem(BaseModel):
    field: str
    label: str        # field name in the user's language, e.g. "Fecha de nacimiento"
    spoken: str       # one sentence in the user's language reading this value back


class RecapOut(BaseModel):
    intro: str
    items: list[RecapItem]
    outro: str        # tell them to say what's wrong, or tap "Everything is correct"


def _flat_profile(profile: dict) -> dict:
    flat = {}
    for k, e in profile.items():
        if k in DERIVED or k.startswith("_"):
            continue
        if k == "household_members" and isinstance(e, list):
            if e:
                flat[k] = {"value": e, "low_confidence": False}
            continue
        if not isinstance(e, dict) or e.get("skipped"):
            continue
        if e.get("value") in (None, "", []):
            continue
        flat[k] = {"value": e["value"], "low_confidence": (e.get("confidence") or 0) < 0.8}
    return flat


def make_recap(language: str, profile: dict, form_name: str, blank_fields: list[str]) -> dict:
    lang = LANGUAGES.get(language, "English")
    flat = _flat_profile(profile)
    prompt = (
        f"Read back this information for the form '{form_name or 'the form'}'. One item per field, same order, every field.\n"
        "For low_confidence fields, say clearly that you are NOT sure and ask them to check it.\n"
        "Read numbers digit by digit and spell names letter by letter only if low_confidence.\n"
        f"Data (JSON): {json.dumps(flat, ensure_ascii=False)}\n"
        + (f"These form fields stay blank on purpose and the user must fill them on paper (mention once in outro; for immigration/citizenship say to get help from a caseworker or legal aid): {blank_fields}\n" if blank_fields else "")
    )
    out: RecapOut = structured_call(prompt, RecapOut, STYLE.format(lang=lang), temperature=0.3)
    items = []
    for it in out.items:
        if it.field not in flat:
            continue
        items.append({**it.model_dump(), "value": flat[it.field]["value"], "low_confidence": flat[it.field]["low_confidence"]})
    script = " ".join([out.intro] + [i["spoken"] for i in items] + [out.outro])
    return {"intro": out.intro, "items": items, "outro": out.outro, "script": script,
            "needs_confirmation": [i["field"] for i in items if i["low_confidence"]]}


# ---------- /recap/correct ----------
class CorrectOut(BaseModel):
    transcript: str
    action: Literal["confirm_all", "confirm_field", "correct", "repeat", "unclear"]
    field: str        # which profile field; "" if none
    new_value: str    # English/Latin normalized; "" unless action == correct
    confidence: float
    reply: str        # in the user's language


def recap_correct(language: str, profile: dict, audio_b64: str, mime_type: str, current_field: str = "") -> dict:
    lang = LANGUAGES.get(language, "English")
    flat = _flat_profile(profile)
    prompt = (
        "The user just heard a read-back of their form data and is responding by voice.\n"
        f"Data (JSON): {json.dumps(flat, ensure_ascii=False)}\n"
        + (f"We were just asking about field: {current_field}\n" if current_field else "")
        + "action: confirm_all = everything is right; confirm_field = the field being discussed is right; "
        "correct = they give a new value for a field (pick the field key from the data); repeat = read it again; unclear.\n"
        "If they say something is wrong but don't give the new value, action=correct with new_value='' and ask for the right value in reply.\n"
        "reply: confirm the change back to them (digits one by one), in their language."
    )
    out: CorrectOut = structured_call([prompt, audio_part(audio_b64, mime_type)], CorrectOut, STYLE.format(lang=lang))
    new_profile = dict(profile)
    # household_members is a plain list, not a {value, ...} entry: never overwrite it with a string
    # (the user can fix it on the review screen).
    if out.action == "correct" and out.field and out.new_value and out.field != "household_members":
        value = coerce(out.field, out.new_value) if out.field in FIELD_TYPES else out.new_value
        new_profile[out.field] = {"value": value, "confidence": max(0.9, out.confidence),
                                  "source": "gap_voice", "user_confirmed": True}
    elif out.action == "confirm_field" and isinstance(new_profile.get(out.field), dict):
        new_profile[out.field] = {**new_profile[out.field], "confidence": 1.0, "user_confirmed": True}
    return {**out.model_dump(), "profile": add_derived(new_profile)}
