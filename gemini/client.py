"""Shared Gemini helper: audio (optional) + prompt → validated Pydantic object.

Privacy: logs only model, schema name, latency and error class. Never audio,
transcripts, values or the profile.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from google import genai
from google.genai import errors, types
from pydantic import BaseModel, ValidationError

log = logging.getLogger("gemini")

MAX_AUDIO_BYTES = 15 * 1024 * 1024  # inline request limit is 20 MB total
_RETRYABLE_CODES = {429, 500, 502, 503, 504}
_MIME_ALIASES = {
    "audio/x-wav": "audio/wav",
    "audio/wave": "audio/wav",
    "audio/mpeg": "audio/mp3",
    "audio/x-m4a": "audio/aac",
    "audio/mp4": "audio/aac",
}

_client: genai.Client | None = None


class GeminiError(Exception):
    def __init__(self, message: str, retryable: bool = True):
        super().__init__(message)
        self.retryable = retryable


def get_client() -> genai.Client:
    global _client
    if _client is None:
        key = os.getenv("GEMINI_API_KEY")
        if not key:
            raise GeminiError(
                "GEMINI_API_KEY is not set (.env at the repo root)", retryable=False
            )
        _client = genai.Client(
            api_key=key, http_options=types.HttpOptions(timeout=45_000)
        )
    return _client


def clean_mime(mime_type: str | None) -> str:
    """'audio/webm;codecs=opus' → 'audio/webm'."""
    m = (mime_type or "audio/webm").split(";")[0].strip().lower()
    return _MIME_ALIASES.get(m, m)


def prepare_audio(audio: bytes, mime_type: str | None) -> tuple[bytes, str]:
    """Optionally convert to 16 kHz mono WAV with ffmpeg (set AUDIO_CONVERT_TO_WAV=1).

    Use this if Gemini rejects the browser's webm recordings.
    """
    mime = clean_mime(mime_type)
    if os.getenv("AUDIO_CONVERT_TO_WAV", "0") != "1" or mime == "audio/wav":
        return audio, mime
    if not shutil.which("ffmpeg"):
        raise GeminiError(
            "AUDIO_CONVERT_TO_WAV=1 but ffmpeg is not installed", retryable=False
        )
    with tempfile.TemporaryDirectory() as d:
        src, dst = Path(d) / "in", Path(d) / "out.wav"
        src.write_bytes(audio)
        r = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-i",
                str(src),
                "-ac",
                "1",
                "-ar",
                "16000",
                str(dst),
            ],
            capture_output=True,
            check=False,
            timeout=30,
        )
        if r.returncode != 0:
            raise GeminiError("Could not convert the audio recording", retryable=False)
        return dst.read_bytes(), "audio/wav"


def call_audio_json(
    *,
    audio: bytes | None,
    mime_type: str | None,
    system_instruction: str,
    prompt: str,
    schema: type[BaseModel],
    temperature: float = 0.2,
) -> BaseModel:
    """One structured Gemini call. Raises GeminiError on any failure (after one retry).

    The retry goes to GEMINI_FALLBACK_MODEL when it is set (useful on the free tier,
    where each model has its own requests-per-minute quota); otherwise it retries the
    same model after the delay the API asks for (capped at 10 s).
    """
    model = os.getenv("GEMINI_MODEL")
    if not model:
        raise GeminiError(
            "GEMINI_MODEL is not set (.env at the repo root)", retryable=False
        )
    fallback = os.getenv("GEMINI_FALLBACK_MODEL") or model

    parts: list = []
    if audio:
        if len(audio) > MAX_AUDIO_BYTES:
            raise GeminiError(
                "Recording is too long. Please answer in under a minute.",
                retryable=False,
            )
        data, mime = prepare_audio(audio, mime_type)
        parts.append(types.Part.from_bytes(data=data, mime_type=mime))
    parts.append(prompt)

    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        response_mime_type="application/json",
        response_schema=schema,
        temperature=temperature,
    )
    client = get_client()

    last_err: GeminiError | None = None
    for attempt, current in enumerate((model, fallback)):
        t0 = time.monotonic()
        try:
            resp = client.models.generate_content(
                model=current, contents=parts, config=config
            )
        except errors.APIError as e:
            retryable = e.code in _RETRYABLE_CODES
            log.warning(
                "gemini error model=%s schema=%s code=%s attempt=%d",
                current,
                schema.__name__,
                e.code,
                attempt,
            )
            if e.code == 429:
                msg = "Gemini is busy (rate limit). Please try again in a few seconds."
            elif e.code == 402:
                msg = "Gemini API credits are used up. Add credit in AI Studio billing."
            else:
                msg = f"Gemini API error {e.code}"
            last_err = GeminiError(msg, retryable)
            if retryable and attempt == 0:
                if fallback == model:
                    time.sleep(min(_retry_delay(e), 10.0))
                continue
            raise last_err from None
        except Exception as e:  # noqa: BLE001  (network errors, timeouts)
            log.warning(
                "gemini error model=%s schema=%s err=%s attempt=%d",
                current,
                schema.__name__,
                type(e).__name__,
                attempt,
            )
            last_err = GeminiError(f"Could not reach Gemini ({type(e).__name__})", True)
            if attempt == 0:
                time.sleep(1.0)
                continue
            raise last_err from None

        log.info(
            "gemini ok model=%s schema=%s ms=%d",
            current,
            schema.__name__,
            (time.monotonic() - t0) * 1000,
        )
        parsed = resp.parsed
        if isinstance(parsed, schema):
            return parsed
        text = resp.text
        if not text:
            last_err = GeminiError("Gemini returned an empty response", True)
        else:
            try:
                return schema.model_validate_json(text)
            except ValidationError:
                last_err = GeminiError(
                    "Gemini returned JSON that didn't match the schema", True
                )
        log.warning("gemini bad output schema=%s attempt=%d", schema.__name__, attempt)
    raise last_err or GeminiError("Gemini call failed", True)


def _retry_delay(e: errors.APIError) -> float:
    """Seconds the API asks us to wait (RetryInfo.retryDelay like "8s"), default 1."""
    try:
        for d in (e.details or {}).get("error", {}).get("details", []):
            if str(d.get("@type", "")).endswith("RetryInfo"):
                return float(str(d.get("retryDelay", "1s")).rstrip("s")) + 0.5
    except (AttributeError, TypeError, ValueError):
        pass
    return 1.0
