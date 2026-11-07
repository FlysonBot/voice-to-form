"""Prompt builders for the audio → JSON calls. Iterate on these with scripts/try_audio.py."""

from __future__ import annotations

import json

from .profile_fields import ONBOARDING_FIELDS

LANGUAGE_NAMES = {
    "es": "Spanish",
    "en": "English",
    "vi": "Vietnamese",
    "tl": "Tagalog",
    "zh": "Simplified Chinese",
    "ar": "Arabic",
    "so": "Somali",
    "ko": "Korean",
    "ru": "Russian",
    "fa": "Persian",
    "pt": "Portuguese",
    "uk": "Ukrainian",
}


def language_name(code: str) -> str:
    return LANGUAGE_NAMES.get((code or "").lower().split("-")[0], code or "Spanish")


CONFIDENCE_RUBRIC = """Confidence (0 to 1) for each value:
- 0.95-1.0: the user said it clearly and directly.
- 0.8-0.9: clear, but you inferred or normalized it (e.g. "my husband and two kids" -> household_size 4).
- 0.5-0.7: audio unclear, answer ambiguous, or you guessed the spelling.
- A name that was NOT spelled out letter by letter is at most 0.7. Spelled out: 0.9+."""

VALUE_FORMATS = """Value formats (every value is a string):
- name: English/Latin letters, capitalized. Transliterate non-Latin scripts.
- date: YYYY-MM-DD. phone: digits only. zip: 5 digits. email: lowercase, no spaces.
- number: plain number, no $ or commas (e.g. "1850.50"). int: digits only.
- bool: "yes" or "no".
- enum: exactly one of the listed options. list_enum: comma-separated listed options.
- Spoken numbers in any language become digits ("cuatro cinco seis" -> "456", "mil quinientos" -> "1500")."""


def onboarding_system(language: str) -> str:
    lang = language_name(language)
    return f"""You are a warm, patient helper in "Tell Us Once", an app that helps families in San Diego fill out benefits forms by voice. You are interviewing the user out loud to build their profile.

Talking to the user:
- next_question MUST be in {lang}, whatever language the user spoke. Simple everyday words, polite/formal "you".
- Ask ONE short question per turn. Closely related parts (street, city, ZIP) may be asked together. Never read a checklist.
- When it helps, start with a very short acknowledgement ("Gracias.") before the question. No long recaps.
- Never ask about immigration or citizenship status, Social Security numbers, bank accounts or utility account numbers. If the user volunteers them, ignore them and do not put them anywhere.
- If the user asks you something, answer in one short sentence, then repeat your question.

Filling the JSON:
- transcript: what the user said, word for word, in the language they spoke.
- updates: only allowed keys. Extract EVERY field the answer contains, even ones you did not ask about. One answer can fill several keys.
- Income: record the amount the user says (income_amount) and how often (income_frequency). Never convert it to monthly yourself.
- household_members: the OTHER people in the home (not the user). If this answer adds or changes anything about them, return the complete updated list starting from the known members; otherwise null. Unknown first_name / date_of_birth stay null. household_members_confidence is one score for the list.
- skipped_keys: fields the user declines ("skip", "I don't know", "I'd rather not", "leave it blank"). If they have no children in school, skip children_schools. If they get no other benefits, skip benefits_other.
- mailing_address: if it is the same as home, the value is "same_as_home".
- intent: "correction" when the user fixes an earlier answer (include the corrected keys in updates); "unclear" when you could not understand the audio (no updates, next_question gently asks them to repeat); "question" / "off_topic" as appropriate (no updates).

{VALUE_FORMATS}

{CONFIDENCE_RUBRIC}"""


def _field_line(key: str) -> str:
    s = ONBOARDING_FIELDS[key]
    opts = f" options={list(s.options)}" if s.options else ""
    opt = " (optional, can be skipped)" if s.optional else ""
    return f"- {key} [{s.type}{opts}]{opt}: {s.description}"


def onboarding_prompt(
    *,
    profile: dict,
    remaining: list[str],
    last_question: str | None,
    transcript: str | None,
) -> str:
    """Extraction prompt. `transcript` is the user's answer, already transcribed by a
    separate plain transcription call (None on the first, audio-less turn).

    Extracting from text instead of audio matters: when the audio went straight into
    this long prompt, Gemini misheard values ("92115" -> the already-known "92105",
    "junio" -> "julio"), while plain transcription of the same clips was correct.
    """
    known = {
        k: v.get("value")
        for k, v in (profile or {}).items()
        if isinstance(v, dict) and v.get("value") is not None and k in ONBOARDING_FIELDS
    }
    remaining_lines = "\n".join(_field_line(k) for k in remaining) or "(nothing left)"
    if transcript is not None:
        task = (
            f'The user\'s spoken answer to your last question, transcribed: "{transcript}"\n\n'
            "Fill the JSON from this answer (transcript = that text, unchanged). Values the user "
            "states override anything in Already known. Then write next_question about the first "
            "remaining field this answer did NOT fill. If this answer filled or skipped everything "
            "remaining, next_question thanks the user and says their profile is ready."
        )
    else:
        task = (
            'There is no answer yet: the conversation is starting. transcript is "", intent is '
            '"answer", updates and skipped_keys are empty, household_members is null. next_question: greet '
            "the user in one sentence, say we don't store their information, and ask about the first "
            "remaining field."
        )
    return f"""Your last question: {last_question or "(none yet)"}

Already known (key: value):
{json.dumps(known, ensure_ascii=False, indent=0) if known else "(nothing yet)"}

Remaining fields, in the order to ask:
{remaining_lines}

{task}"""


def voice_answer_system(language: str) -> str:
    lang = language_name(language)
    return f"""You turn one spoken answer into the value of one form field for "Tell Us Once", an app that helps families in San Diego fill out benefits forms.

- transcript: what the user said, word for word, in the language they spoke.
- status: "answered" if they gave a usable value; "skipped" if they decline or don't know; "leave_blank" if they say to leave it blank / they'll write it on paper; "unclear" if you can't understand it or it doesn't answer the question.
- value: the field value in the requested format, or null unless status is "answered".
- retry_question: ALWAYS write one short, polite question in {lang} asking for this field again (it is used if the answer can't be used).
- Never comment on immigration status. Values that go on the form use English/Latin letters.

{VALUE_FORMATS}
- digits: only the digits, in order, no spaces or dashes.

{CONFIDENCE_RUBRIC}"""


def voice_answer_prompt(
    *, field: dict, question: str | None, form_id: str | None
) -> str:
    opts = f"\nAllowed options: {field['options']}" if field.get("options") else ""
    desc = (
        f"\nWhat it is: {field['description_en']}"
        if field.get("description_en")
        else ""
    )
    return f"""Form: {form_id or "(unknown)"}
Field: {field["label_en"]} (key {field["key"]}, format {field["type"]}){desc}{opts}
Question the user heard: {question or "(a question asking for this field)"}

Listen to the user's answer and fill the JSON."""


TRANSCRIBE_SYSTEM = "You transcribe audio."

# Words a San Diego benefits conversation is likely to contain. Helps transcription of
# proper nouns ("San Diego Unified" was heard as "San Juan de Lurigancho" without it).
LOCAL_VOCABULARY = (
    "San Diego, San Diego Unified, Chula Vista, City Heights, National City, El Cajon, "
    "Medi-Cal, CalFresh, WIC, SSI, SDG&E, CARE, LIHEAP, MTS, PRONTO, EBT"
)


def transcribe_prompt(question: str | None, language: str) -> str:
    """Transcription with light context: the question just asked and local words.

    Never include already-known profile values here: they bias what Gemini "hears"
    (a spoken ZIP correction came back as the old ZIP).
    """
    asked = f'The user is answering this question: "{question}"\n' if question else ""
    return (
        f"{asked}The user probably speaks {language_name(language)}. Words that may "
        f"come up: {LOCAL_VOCABULARY}.\n"
        "Transcribe the audio word for word in the language spoken (short answers like "
        "a single word are normal), and give the language's ISO 639-1 code in "
        "language_detected. Write only what was said; do not guess missing words."
    )


TRANSCRIBE_PROMPT = (
    "Transcribe this audio word for word in the language spoken, and give the "
    "language's ISO 639-1 code in language_detected."
)


# Number-like gap fields get a deliberately short prompt. In testing, the long
# voice_answer_system() prompt garbled spoken digit strings ("cero uno dos tres" →
# "0003...") while a plain transcription prompt got them right every time.
NUMBER_FIELD_TYPES = {"digits", "phone", "zip"}


def number_answer_system(language: str) -> str:
    return (
        "You transcribe a spoken number for a form field. transcript: exactly what "
        "was said, word for word. value: only the digits the speaker said, in order, "
        "nothing added or removed (null if they gave no number). status: answered, "
        "skipped (they decline or don't know), leave_blank (they'll write it on "
        "paper) or unclear. confidence: 0 to 1. retry_question: one short polite "
        f"question in {language_name(language)} asking for the number again."
    )


def number_answer_prompt(*, field: dict) -> str:
    return f"Field: {field['label_en']}. Transcribe the answer."
