import json

import pytest
from fastapi.testclient import TestClient
from google import genai
from google.genai import _transformers

from gemini import onboarding, voice_answer
from gemini import router as router_mod
from gemini.client import GeminiError, clean_mime
from gemini.dev_app import app
from gemini.schemas import (
    OnboardingExtraction,
    Session,
    Transcription,
    VoiceAnswerExtraction,
    VoiceAnswerState,
)

client = TestClient(app)


def ext(**kw):
    base = {
        "transcript": "t",
        "intent": "answer",
        "updates": [],
        "household_members": None,
        "household_members_confidence": None,
        "skipped_keys": [],
        "next_question": "¿?",
    }
    base.update(kw)
    return OnboardingExtraction.model_validate(base)


@pytest.mark.parametrize(
    "schema", [OnboardingExtraction, VoiceAnswerExtraction, Transcription]
)
def test_schemas_convert_for_gemini(schema):
    _transformers.t_schema(genai.Client(api_key="dummy"), schema)


def test_clean_mime():
    assert clean_mime("audio/webm;codecs=opus") == "audio/webm"
    assert clean_mime(None) == "audio/webm"
    assert clean_mime("audio/x-wav") == "audio/wav"


def test_multi_field_answer_fills_size_and_members():
    e = ext(
        updates=[{"key": "household_size", "value": "4", "confidence": 0.9}],
        household_members=[
            {"first_name": "Jose", "relationship": "spouse", "date_of_birth": None},
            {"first_name": None, "relationship": "child", "date_of_birth": None},
            {"first_name": None, "relationship": "child", "date_of_birth": None},
        ],
        household_members_confidence=0.85,
    )
    r = onboarding.apply_extraction(Session(language="es"), e, has_audio=True)
    assert r.profile["household_size"]["value"] == 4
    assert len(r.profile["household_members"]["value"]) == 3
    assert set(r.updated_keys) == {"household_size", "household_members"}
    assert "household_members" in r.remaining  # names/DOBs still missing
    assert not r.done


def test_bad_values_rejected_and_unclear_ignored():
    e = ext(
        updates=[
            {"key": "phone", "value": "555", "confidence": 0.9},
            {"key": "address_zip", "value": "92105", "confidence": 0.9},
        ]
    )
    r = onboarding.apply_extraction(Session(), e, has_audio=True)
    assert r.rejected_keys == ["phone"] and r.updated_keys == ["address_zip"]

    e = ext(
        intent="unclear",
        updates=[{"key": "address_zip", "value": "92105", "confidence": 0.9}],
    )
    r = onboarding.apply_extraction(Session(), e, has_audio=True)
    assert r.updated_keys == [] and r.profile == {}


def test_skip_and_correction():
    state = Session(
        profile={
            "address_zip": {
                "value": "92105",
                "confidence": 0.95,
                "source": "onboarding_voice",
            }
        },
        skipped=["email"],
    )
    e = ext(
        intent="correction",
        updates=[{"key": "address_zip", "value": "92115", "confidence": 0.9}],
        skipped_keys=["gender"],
    )
    r = onboarding.apply_extraction(state, e, has_audio=True)
    assert r.profile["address_zip"]["value"] == "92115"
    assert r.skipped == ["email", "gender"]


def test_previously_skipped_field_answered_is_unskipped():
    e = ext(updates=[{"key": "email", "value": "a@b.co", "confidence": 0.9}])
    r = onboarding.apply_extraction(Session(skipped=["email"]), e, has_audio=True)
    assert r.skipped == []


def test_first_turn_without_audio_ignores_updates():
    e = ext(updates=[{"key": "address_zip", "value": "92105", "confidence": 0.9}])
    r = onboarding.apply_extraction(Session(), e, has_audio=False)
    assert r.profile == {} and r.transcript == "" and r.remaining[0] == "phone"


def _answer(**kw):
    base = {
        "transcript": "t",
        "status": "answered",
        "value": "0123 4567 890",
        "confidence": 0.95,
        "retry_question": "¿Me lo repite?",
    }
    base.update(kw)
    return VoiceAnswerExtraction.model_validate(base)


def test_voice_answer_sensitive_cap_and_unclear():
    st = VoiceAnswerState(
        field={
            "key": "sdge_account_number",
            "label_en": "SDG&E account number",
            "type": "digits",
            "sensitive": True,
        }
    )
    r = voice_answer.apply_answer(st, _answer())
    assert (
        r.value == "01234567890"
        and r.confidence == 0.79
        and r.clarification_question is None
    )

    r = voice_answer.apply_answer(st, _answer(value="no sé"))
    assert (
        r.status == "unclear"
        and r.value is None
        and r.clarification_question == "¿Me lo repite?"
    )

    r = voice_answer.apply_answer(st, _answer(status="leave_blank", value=None))
    assert r.status == "leave_blank" and r.value is None and r.confidence == 0


# ---------- routes ----------


FIELD_X = json.dumps({"key": "x", "label_en": "X"})
AUDIO = {"audio": ("a.webm", b"x", "audio/webm")}


def test_mock_routes():
    r = client.post("/onboarding/turn?mock=true", data={"session": "{}"})
    assert r.status_code == 200 and "next_question" in r.json()
    r = client.post("/voice/answer?mock=true", data={"session": "{}"})
    assert r.status_code == 200 and r.json()["source"] == "gap_voice"


def test_onboarding_route_with_fake_gemini(monkeypatch):
    captured = {}

    def fake_call(**kw):
        if kw["schema"] is Transcription:
            captured["transcribe"] = kw
            return Transcription(
                transcript="Es el 619 555 0142.", language_detected="es"
            )
        captured.update(kw)
        return ext(
            transcript="(gemini echo)",
            updates=[{"key": "phone", "value": "619 555 0142", "confidence": 0.95}],
        )

    monkeypatch.setattr(onboarding, "call_audio_json", fake_call)
    session = {
        "language": "es",
        "profile": {},
        "skipped": [],
        "last_question": "¿Su teléfono?",
        "selected_form": None,
        "suggested_programs": [],  # other shared-format keys are ignored
        "confirmed": False,
    }
    r = client.post(
        "/onboarding/turn",
        data={"session": json.dumps(session)},
        files={"audio": ("a.webm", b"fakeaudio", "audio/webm;codecs=opus")},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["profile"]["phone"]["value"] == "6195550142"
    assert body["remaining"][0] == "email"
    # Step 1 transcribes the audio; step 2 extracts from that text without audio.
    assert captured["transcribe"]["audio"] == b"fakeaudio"
    assert "¿Su teléfono?" in captured["transcribe"]["prompt"]  # question as context
    assert "Medi-Cal" in captured["transcribe"]["prompt"]
    assert captured["audio"] is None
    assert "Es el 619 555 0142." in captured["prompt"]
    assert "Spanish" in captured["system_instruction"]
    assert body["transcript"] == "Es el 619 555 0142."


def test_voice_answer_builds_state_from_session(monkeypatch):
    seen = {}

    def fake_parse(state, audio, mime):
        seen["state"] = state
        return voice_answer.apply_answer(
            state,
            VoiceAnswerExtraction.model_validate(
                {
                    "transcript": "t",
                    "status": "answered",
                    "value": "92105",
                    "confidence": 0.9,
                    "retry_question": "?",
                }
            ),
        )

    monkeypatch.setattr(router_mod, "parse_voice_answer", fake_parse)
    session = {"language": "vi", "selected_form": "sdge_care", "profile": {}}
    r = client.post(
        "/voice/answer",
        data={
            "session": json.dumps(session),
            "field": json.dumps({"key": "zip", "label_en": "ZIP", "type": "zip"}),
            "question": "Mã ZIP của bạn là gì?",
        },
        files=AUDIO,
    )
    assert r.status_code == 200 and r.json()["value"] == "92105"
    st = seen["state"]
    assert (st.language, st.form_id, st.question) == (
        "vi",
        "sdge_care",
        "Mã ZIP của bạn là gì?",
    )


def test_gemini_error_becomes_502(monkeypatch):
    def boom(**kw):
        raise GeminiError("Gemini API error 503", retryable=True)

    monkeypatch.setattr(voice_answer, "call_audio_json", boom)
    r = client.post(
        "/voice/answer",
        data={"session": json.dumps({"language": "es"}), "field": FIELD_X},
        files=AUDIO,
    )
    assert r.status_code == 502 and r.json() == {
        "error": "Gemini API error 503",
        "retryable": True,
    }


def test_bad_input_is_422_without_echoing_values():
    r = client.post(
        "/voice/answer",
        data={"session": "{}", "field": json.dumps({"label_en": "SSN 123-45-6789"})},
        files=AUDIO,
    )
    assert r.status_code == 422 and "123-45" not in r.text
    assert r.json()["error"] == "invalid field: key"
    r = client.post("/onboarding/turn", data={"session": "not json"})
    assert r.status_code == 422 and r.json()["error"] == "session is not valid JSON"
    r = client.post("/voice/answer", data={"session": "{}"}, files=AUDIO)
    assert r.status_code == 422 and r.json()["error"] == "field is required"


def test_voice_answer_requires_audio():
    r = client.post("/voice/answer", data={"session": "{}", "field": FIELD_X})
    assert r.status_code == 400


def test_unspelled_names_need_confirmation():
    e = ext(
        transcript="Me llamo María Elena López. López se escribe L, O, P, E, Z.",
        updates=[
            {"key": "first_name", "value": "Maria", "confidence": 1.0},
            {"key": "middle_name", "value": "Elena", "confidence": 1.0},
            {"key": "last_name", "value": "Lopez", "confidence": 1.0},
        ],
    )
    r = onboarding.apply_extraction(Session(), e, has_audio=True)
    conf = {
        k: r.profile[k]["confidence"]
        for k in ("first_name", "middle_name", "last_name")
    }
    assert conf == {"first_name": 0.7, "middle_name": 0.7, "last_name": 1.0}


@pytest.mark.parametrize(
    "name,transcript,expected",
    [
        ("Lopez", "se escribe L-O-P-E-Z", True),
        ("López", "l, o, p, e, z", True),
        ("Lopez", "Me llamo Lopez", False),
        ("Ana", "mi hija Ana", False),
        ("Ana", "A. N. A.", True),
    ],
)
def test_spelled_out(name, transcript, expected):
    assert onboarding.spelled_out(name, transcript) is expected


@pytest.mark.parametrize("said", ["No", "none", "Nada.", "null"])
def test_none_answer_for_optional_text_is_a_skip(said):
    e = ext(updates=[{"key": "benefits_other", "value": said, "confidence": 1.0}])
    r = onboarding.apply_extraction(Session(), e, has_audio=True)
    assert "benefits_other" not in r.profile and "benefits_other" in r.skipped
    assert r.rejected_keys == []


def test_unchanged_member_list_is_not_an_update():
    members = [{"first_name": "Jose", "relationship": "spouse", "date_of_birth": None}]
    profile = {
        "household_members": {
            "value": members,
            "confidence": 0.9,
            "source": "onboarding_voice",
        }
    }
    e = ext(household_members=members, household_members_confidence=0.9)
    r = onboarding.apply_extraction(Session(profile=profile), e, has_audio=True)
    assert r.updated_keys == []
