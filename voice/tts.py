"""Gemini text-to-speech -> base64 WAV.

Older Gemini TTS models return raw 16-bit PCM, mono, 24 kHz; we wrap it in a WAV
header so the browser can play it. Newer ones (e.g. gemini-3.8-flash-tts) return WAV
already, which is passed through unchanged.
If this fails or is slow, the frontend falls back to window.speechSynthesis.
"""
import base64
import io
import os
import wave

from google.genai import types

from .gemini_client import client, tts_model

VOICE = os.environ.get("GEMINI_TTS_VOICE") or "Kore"  # any prebuilt Gemini voice


def pcm_to_wav(pcm: bytes, rate: int = 24000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)
    return buf.getvalue()


def synthesize(text: str) -> str:
    """Returns base64-encoded WAV. Raises on failure (caller handles it)."""
    resp = client().models.generate_content(
        model=tts_model(),
        contents=text,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=VOICE)
                )
            ),
        ),
    )
    part = resp.candidates[0].content.parts[0]
    data = part.inline_data.data
    if isinstance(data, str):  # some SDK versions hand back base64 text
        data = base64.b64decode(data)
    mime = (part.inline_data.mime_type or "").lower()
    if mime.startswith(("audio/wav", "audio/x-wav", "audio/wave")) or data[:4] == b"RIFF":
        return base64.b64encode(data).decode()  # newer TTS models already return a WAV file
    rate = 24000
    if "rate=" in mime:
        try:
            rate = int(mime.split("rate=")[1].split(";")[0])
        except ValueError:
            pass
    return base64.b64encode(pcm_to_wav(data, rate)).decode()
