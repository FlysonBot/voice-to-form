"""Real-Gemini smoke test for the voice module — no microphone needed.

It uses Gemini TTS to *speak* fake Spanish answers, then feeds that audio back
through onboarding, gap answers, recap and recap correction. All data is fake.

Run from the repo root:   uv run python -m voice.smoke_test
Needs .env (repo root) with GEMINI_API_KEY, GEMINI_MODEL, GEMINI_TTS_MODEL.
"""
import base64
import json
import os
import sys
import time

from dotenv import load_dotenv

load_dotenv()

OK, FAIL = "\033[32m✓\033[0m", "\033[31m✗\033[0m"
results = []


def step(name, fn):
    t = time.time()
    try:
        out = fn()
        print(f"{OK} {name}  ({time.time() - t:.1f}s)")
        results.append(True)
        return out
    except Exception as e:
        print(f"{FAIL} {name}: {type(e).__name__}: {e}")
        results.append(False)
        return None


def main():
    for var in ("GEMINI_API_KEY", "GEMINI_MODEL", "GEMINI_TTS_MODEL"):
        if not os.environ.get(var):
            sys.exit(f"{FAIL} {var} missing in .env (repo root)")

    from .gaps_recap import make_question, make_recap, parse_answer, recap_correct
    from .onboarding import onboarding_turn
    from .tts import synthesize

    # 1. TTS: also produces the fake "user" audio for the next steps
    def say(text):
        return synthesize(text)

    hello = step("TTS speaks Spanish", lambda: say("Hola, vamos a llenar su formulario."))
    if hello:
        os.makedirs("smoke_out", exist_ok=True)
        with open("smoke_out/tts_sample.wav", "wb") as f:
            f.write(base64.b64decode(hello))
        print("   -> listen to smoke_out/tts_sample.wav")

    household_audio = step("Make fake answer audio", lambda: say(
        "Me llamo María López. Vivo con mi esposo José y mis dos hijos, Sofía y Mateo."))
    if not household_audio:
        sys.exit("TTS is required for the rest of the test (it creates the fake voice answers).")

    # 2. Onboarding: first turn (greeting), then a spoken answer filling several fields
    first = step("Onboarding greeting (no audio)", lambda: onboarding_turn("es", {}, None, "audio/wav", ""))
    if first:
        print("   question:", first["say"])
    turn = step("Onboarding turn with spoken answer", lambda: onboarding_turn(
        "es", first["profile"] if first else {}, household_audio, "audio/wav",
        first["say"] if first else "¿Cómo se llama y quién vive con usted?"))
    if turn:
        p = turn["profile"]
        print("   transcript:", turn["transcript"])
        print("   filled:", turn["updated_fields"])
        print("   household_members:", json.dumps(p.get("household_members"), ensure_ascii=False))
        print("   next question:", turn["say"])
        check("first_name == Maria", str(p.get("first_name", {}).get("value", "")).lower().startswith("mar"))
        check("household_size == 4", p.get("household_size", {}).get("value") == 4)
        check("household_members has 3 people", isinstance(p.get("household_members"), list) and len(p["household_members"]) == 3)

    # 3. Gap question + spoken answer with digits
    q = step("Gap question for SDG&E account number", lambda: make_question(
        "es", "sdge_account_number", "SDG&E account number from the energy bill", "SDG&E CARE"))
    if q:
        print("   question:", q["question"])
    acct_audio = say("Mi número de cuenta es uno dos tres cuatro, cinco seis siete ocho, nueve cero.")
    ans = step("Parse spoken account number", lambda: parse_answer(
        "es", "sdge_account_number", "SDG&E account number", q["question"] if q else "", acct_audio, "audio/wav"))
    if ans:
        print("   intent:", ans["intent"], "| value:", ans["value"], "| reply:", ans["reply"])
        check("intent == answer", ans["intent"] == "answer")
        check("digits 1234567890", ans["value"].replace(" ", "").replace("-", "") == "1234567890")

    blank_audio = say("No lo tengo aquí, déjelo en blanco por favor.")
    blank = step("Parse 'leave it blank'", lambda: parse_answer(
        "es", "ssn", "Social Security number", "¿Cuál es su número de Seguro Social?", blank_audio, "audio/wav"))
    if blank:
        check("intent is leave_blank/skip", blank["intent"] in ("leave_blank", "skip"))

    wrong_audio = say("No, eso está mal.")
    wrong = step("Parse 'that's wrong'", lambda: parse_answer(
        "es", "sdge_account_number", "SDG&E account number", "¿Cuál es su número de cuenta?", wrong_audio, "audio/wav"))
    if wrong:
        check("intent == wrong", wrong["intent"] == "wrong")

    # 4. Recap + correction
    profile = turn["profile"] if turn else {}
    profile["last_name"] = {"value": "Lopez", "confidence": 0.6, "source": "onboarding_voice"}  # force a yellow field
    rec = step("Recap in Spanish", lambda: make_recap("es", profile, "SDG&E CARE", ["citizenship_status"]))
    if rec:
        print("   script:", rec["script"][:300], "...")
        check("last_name needs confirmation", "last_name" in rec["needs_confirmation"])

    fix_audio = say("Mi apellido está mal, es López con S al final: L, O, P, E, S.")
    fix = step("Spoken correction in recap", lambda: recap_correct("es", profile, fix_audio, "audio/wav"))
    if fix:
        print("   action:", fix["action"], "| field:", fix["field"], "| new:", fix["new_value"], "| reply:", fix["reply"])
        check("last_name corrected to Lopes", fix["field"] == "last_name" and fix["new_value"].lower() == "lopes")

    # 5. Immigration fields are refused
    def refused():
        try:
            make_question("es", "immigration_status", "", "")
        except ValueError:
            return True
        raise AssertionError("immigration_status was NOT refused")
    step("Immigration question refused", refused)

    passed = sum(results)
    print(f"\n{passed}/{len(results)} checks passed")
    sys.exit(0 if passed == len(results) else 1)


def check(name, cond):
    print(f"   {OK if cond else FAIL} {name}")
    results.append(bool(cond))


if __name__ == "__main__":
    main()
