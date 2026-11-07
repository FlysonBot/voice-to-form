"""Shared Gemini helpers for the voice module.

Model names come from .env (GEMINI_MODEL, GEMINI_TTS_MODEL) — never hardcoded.
Never log transcripts, profile values or audio here (privacy rules).
"""
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

_client = None


class ConfigError(RuntimeError):
    """A required .env setting is missing. The message names the variable only (no secrets)."""


def _env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ConfigError(f"{name} is not set. Copy .env.example to .env at the repo root and fill it in.")
    return value


def client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=_env("GEMINI_API_KEY"))
    return _client


def text_model() -> str:
    return _env("GEMINI_MODEL")


def tts_model() -> str:
    return _env("GEMINI_TTS_MODEL")


def audio_part(audio_b64: str, mime_type: str = "audio/wav") -> types.Part:
    import base64

    return types.Part.from_bytes(data=base64.b64decode(audio_b64), mime_type=mime_type)


def structured_call(contents, schema, system: str, temperature: float = 0.2):
    """One Gemini call that always returns a parsed Pydantic object of type `schema`."""
    resp = client().models.generate_content(
        model=text_model(),
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_schema=schema,
            temperature=temperature,
        ),
    )
    if resp.parsed is not None:
        return resp.parsed
    return schema.model_validate_json(resp.text)
