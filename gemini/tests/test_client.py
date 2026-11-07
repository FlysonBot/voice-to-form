from types import SimpleNamespace

import pytest
from google.genai import errors

from gemini import client as gc
from gemini.schemas import Transcription


def _429(delay="3s"):
    body = {
        "error": {
            "code": 429,
            "message": "quota",
            "status": "RESOURCE_EXHAUSTED",
            "details": [
                {
                    "@type": "type.googleapis.com/google.rpc.RetryInfo",
                    "retryDelay": delay,
                }
            ],
        }
    }
    return errors.APIError(429, body)


class FakeClient:
    def __init__(self, outcomes):
        self.outcomes, self.models_called = list(outcomes), []
        self.models = SimpleNamespace(generate_content=self._gen)

    def _gen(self, *, model, contents, config):
        self.models_called.append(model)
        out = self.outcomes.pop(0)
        if isinstance(out, Exception):
            raise out
        return SimpleNamespace(parsed=None, text=out)


OK = '{"transcript": "hola", "language_detected": "es"}'


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "primary")
    monkeypatch.delenv("GEMINI_FALLBACK_MODEL", raising=False)
    sleeps = []
    monkeypatch.setattr(gc.time, "sleep", sleeps.append)
    return monkeypatch, sleeps


def _call():
    return gc.call_audio_json(
        audio=None,
        mime_type=None,
        system_instruction="s",
        prompt="p",
        schema=Transcription,
    )


def test_retry_delay_parsed():
    assert gc._retry_delay(_429("8s")) == 8.5
    assert gc._retry_delay(errors.APIError(500, {"error": {}})) == 1.0


def test_429_without_fallback_waits_then_retries_same_model(env):
    mp, sleeps = env
    fake = FakeClient([_429("3s"), OK])
    mp.setattr(gc, "get_client", lambda: fake)
    assert _call().transcript == "hola"
    assert fake.models_called == ["primary", "primary"] and sleeps == [3.5]


def test_429_with_fallback_switches_model_without_waiting(env):
    mp, sleeps = env
    mp.setenv("GEMINI_FALLBACK_MODEL", "backup")
    fake = FakeClient([_429(), OK])
    mp.setattr(gc, "get_client", lambda: fake)
    assert _call().transcript == "hola"
    assert fake.models_called == ["primary", "backup"] and sleeps == []


def test_two_429s_give_friendly_retryable_error(env):
    mp, _ = env
    mp.setattr(gc, "get_client", lambda: FakeClient([_429(), _429()]))
    with pytest.raises(gc.GeminiError) as e:
        _call()
    assert e.value.retryable and "rate limit" in str(e.value)


def test_bad_json_is_retried(env):
    mp, _ = env
    fake = FakeClient(['{"nope": 1}', OK])
    mp.setattr(gc, "get_client", lambda: fake)
    assert _call().transcript == "hola"
