"""Try the audio → JSON functions on a local clip, without the server or frontend.

  uv run python gemini/scripts/try_audio.py gemini/samples/test.webm --mode transcribe
  uv run python gemini/scripts/try_audio.py --mode onboarding --lang es                 # first turn, no audio
  uv run python gemini/scripts/try_audio.py gemini/samples/es_household.webm --mode onboarding --lang es \
      --state gemini/samples/state.json --last-question "¿Quién vive con usted?"
  uv run python gemini/scripts/try_audio.py gemini/samples/es_account.webm --mode answer --lang es \
      --field-key sdge_account_number --field-label "SDG&E account number" --field-type digits --sensitive

Use FAKE data only. Output is printed to your terminal, never logged.
"""

import argparse
import json
import mimetypes
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv

load_dotenv(REPO_ROOT / ".env")

from gemini.client import GeminiError, call_audio_json
from gemini.onboarding import run_onboarding_turn
from gemini.prompts import TRANSCRIBE_PROMPT
from gemini.schemas import GapField, Session, Transcription, VoiceAnswerState
from gemini.voice_answer import parse_voice_answer

mimetypes.add_type("audio/webm", ".webm")
mimetypes.add_type("audio/ogg", ".ogg")
mimetypes.add_type("audio/aac", ".m4a")


def main():
    p = argparse.ArgumentParser()
    p.add_argument(
        "audio", nargs="?", help="path to a clip (omit for the first onboarding turn)"
    )
    p.add_argument(
        "--mode", choices=["transcribe", "onboarding", "answer"], default="onboarding"
    )
    p.add_argument("--lang", default="es")
    p.add_argument(
        "--state", help="JSON file: onboarding state {profile, skipped, ...}"
    )
    p.add_argument("--last-question")
    p.add_argument("--field-key", default="sdge_account_number")
    p.add_argument("--field-label", default="SDG&E account number")
    p.add_argument("--field-type", default="digits")
    p.add_argument("--sensitive", action="store_true")
    a = p.parse_args()

    audio, mime = None, None
    if a.audio:
        audio = Path(a.audio).read_bytes()
        mime = mimetypes.guess_type(a.audio)[0] or "audio/webm"

    try:
        if a.mode == "transcribe":
            if not audio:
                p.error("transcribe needs an audio file")
            out = call_audio_json(
                audio=audio,
                mime_type=mime,
                system_instruction="You transcribe audio.",
                prompt=TRANSCRIBE_PROMPT,
                schema=Transcription,
            )
        elif a.mode == "onboarding":
            state = json.loads(Path(a.state).read_text()) if a.state else {}
            state.setdefault("language", a.lang)
            if a.last_question:
                state["last_question"] = a.last_question
            out = run_onboarding_turn(Session.model_validate(state), audio, mime)
        else:
            if not audio:
                p.error("answer mode needs an audio file")
            field = GapField(
                key=a.field_key,
                label_en=a.field_label,
                type=a.field_type,
                sensitive=a.sensitive,
            )
            out = parse_voice_answer(
                VoiceAnswerState(language=a.lang, field=field), audio, mime
            )
    except GeminiError as e:
        print(f"GeminiError (retryable={e.retryable}): {e}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(out.model_dump(mode="json"), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
