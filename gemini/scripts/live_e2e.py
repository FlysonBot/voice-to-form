"""Live end-to-end test of the Gemini audio calls (costs a few cents, needs .env).

Runs a full fake Spanish conversation through the real routes:
  1. /onboarding/turn starting from an EMPTY profile, one spoken answer per turn,
     carrying the session forward exactly like the frontend will.
  2. /voice/answer for empty form-specific gap fields, one spoken answer each.
Every step is checked against expected values; prints PASS/FAIL per check.

  uv run python gemini/scripts/live_e2e.py              # everything
  uv run python gemini/scripts/live_e2e.py --only gaps  # just the gap fields

Clips are synthesized with macOS `say` (Spanish voice) + ffmpeg into
gemini/samples/e2e/ (gitignored) as browser-style webm/opus. FAKE data only.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv

load_dotenv(REPO_ROOT / ".env")

from fastapi.testclient import TestClient

from gemini.dev_app import app

CLIPS = REPO_ROOT / "gemini" / "samples" / "e2e"
VOICE = "Flo (Spanish (Mexico))"

# (clip name, what the user says, expected profile values after this turn,
#  keys expected in `skipped`)
ONBOARDING = [
    (
        "01_phone",
        "Mi número es seis uno nueve, cinco cinco cinco, cero uno cuatro dos.",
        {"phone": "6195550142"},
        [],
    ),
    ("02_email", "No tengo correo electrónico.", {}, ["email"]),
    (
        "03_name",
        "Me llamo María Elena López. López se escribe L, O, P, E, Z.",
        {"first_name": "Maria", "middle_name": "Elena", "last_name": "Lopez"},
        [],
    ),
    (
        "04_dob",
        "Nací el catorce de marzo de mil novecientos ochenta y ocho.",
        {"date_of_birth": "1988-03-14"},
        [],
    ),
    ("05_gender", "Mujer.", {"gender": "female"}, []),
    (
        "06_address",
        (
            "Vivo en el cuatro tres dos uno de University Avenue, apartamento siete, "
            "en San Diego, código postal nueve dos uno cero cinco."
        ),
        {"address_city": "San Diego", "address_zip": "92105"},
        [],
    ),
    (
        "07_correction",
        "Perdón, me equivoqué. El código postal es nueve dos uno uno cinco.",
        {"address_zip": "92115"},
        [],
    ),
    ("08_mailing", "Es la misma dirección.", {"mailing_address": "same_as_home"}, []),
    (
        "09_housing",
        "Rentamos. Pagamos mil seiscientos dólares al mes.",
        {"housing_status": "rent", "monthly_housing_cost": 1600},
        [],
    ),
    (
        "10_household",
        "Somos cuatro: yo, mi esposo José y nuestros dos hijos, Ana y Luis.",
        {"household_size": 4},
        [],
    ),
    (
        "11_member_dobs",
        (
            "José nació el dos de junio de mil novecientos ochenta y cinco. "
            "Ana nació el diez de septiembre de dos mil quince, y Luis el veinte de enero de dos mil dieciocho."
        ),
        {},
        [],
    ),
    (
        "12_schools",
        "Ana y Luis van a la primaria Rosa Parks, del distrito San Diego Unified.",
        {},
        [],
    ),
    (
        "13_income",
        "Mi esposo trabaja en construcción y gana unos mil doscientos dólares cada dos semanas.",
        {"income_amount": 1200, "income_frequency": "biweekly", "monthly_income": 2600},
        [],
    ),
    (
        "14_benefits",
        (
            "Tenemos Medi-Cal, y los niños reciben comida gratis en la escuela. "
            "No recibimos CalFresh, ni WIC, ni SSI."
        ),
        {
            "benefits_medi_cal": True,
            "benefits_school_meals": True,
            "benefits_calfresh": False,
            "benefits_wic": False,
            "benefits_ssi": False,
        },
        [],
    ),
    ("15_benefits_other", "No, nada más.", {}, []),
    (
        "16_situations",
        (
            "No. Nadie tiene más de sesenta y cinco años, nadie tiene una discapacidad "
            "y no hay veteranos."
        ),
        {"has_senior_65_plus": False, "has_disability": False, "has_veteran": False},
        [],
    ),
]

MEMBERS_EXPECTED = {  # checked at the end
    ("Jose", "spouse", "1985-06-02"),
    ("Ana", "child", "2015-09-10"),
    ("Luis", "child", "2018-01-20"),
}

# (clip, what the user says, field, expected status, expected value)
GAPS = [
    (
        "g1_account",
        "Mi número de cuenta es cero uno dos tres, cuatro cinco seis siete, ocho nueve cero.",
        {
            "key": "sdge_account_number",
            "label_en": "SDG&E account number",
            "type": "digits",
            "sensitive": True,
        },
        "answered",
        "01234567890",
    ),
    (
        "g2_ssn_blank",
        "Prefiero dejarlo en blanco, lo escribo yo en el papel.",
        {
            "key": "ssn",
            "label_en": "Social Security number",
            "type": "digits",
            "sensitive": True,
        },
        "leave_blank",
        None,
    ),
    (
        "g3_liheap",
        "Sí, el año pasado recibimos ayuda de LIHEAP.",
        {
            "key": "receives_liheap",
            "label_en": "Anyone in the household received LIHEAP in the last 12 months",
            "type": "bool",
        },
        "answered",
        True,
    ),
    (
        "g4_start_date",
        "Nos mudamos aquí el primero de agosto de dos mil veintitrés.",
        {
            "key": "service_start_date",
            "label_en": "Date service started at this address",
            "type": "date",
        },
        "answered",
        "2023-08-01",
    ),
    (
        "g5_unclear",
        "Eh... mmm... no estoy segura, a ver...",
        {"key": "meter_number", "label_en": "Electric meter number", "type": "digits"},
        "unclear",
        None,
    ),
]


def make_clip(name: str, text: str) -> Path:
    CLIPS.mkdir(parents=True, exist_ok=True)
    webm = CLIPS / f"{name}.webm"
    meta = CLIPS / f"{name}.txt"
    if webm.exists() and meta.exists() and meta.read_text() == text:
        return webm
    aiff = CLIPS / f"{name}.aiff"
    subprocess.run(["say", "-v", VOICE, "-o", str(aiff), text], check=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(aiff),
            "-c:a",
            "libopus",
            "-ac",
            "1",
            str(webm),
        ],
        check=True,
    )
    aiff.unlink()
    meta.write_text(text)
    return webm


class Checker:
    def __init__(self):
        self.passed = self.failed = 0

    def check(self, label: str, ok: bool, detail: str = ""):
        if ok:
            self.passed += 1
        else:
            self.failed += 1
            print(f"    FAIL {label} {detail}")


def post(client: TestClient, path: str, data: dict, clip: Path | None):
    files = (
        {"audio": (clip.name, clip.read_bytes(), "audio/webm;codecs=opus")}
        if clip
        else None
    )
    for attempt in range(3):
        t0 = time.monotonic()
        r = client.post(path, data=data, files=files)
        ms = (time.monotonic() - t0) * 1000
        if r.status_code == 502 and r.json().get("retryable") and attempt < 2:
            print(f"    (retrying after: {r.json()['error']})")
            time.sleep(5)
            continue
        return r, ms
    return r, ms


def value(profile: dict, key: str):
    entry = profile.get(key)
    return entry.get("value") if isinstance(entry, dict) else None


def run_onboarding(client: TestClient, c: Checker) -> None:
    print("\n=== Onboarding: empty profile + spoken answers ===")
    session = {"language": "es", "profile": {}, "skipped": [], "last_question": None}

    r, ms = post(client, "/onboarding/turn", {"session": json.dumps(session)}, None)
    body = r.json()
    print(f"[greeting] {r.status_code} {ms:.0f} ms  Q: {body.get('next_question')}")
    c.check("greeting status", r.status_code == 200, body.get("error", ""))
    if r.status_code != 200:
        return
    session["last_question"] = body["next_question"]

    for name, text, expected, expected_skips in ONBOARDING:
        clip = make_clip(name, text)
        r, ms = post(client, "/onboarding/turn", {"session": json.dumps(session)}, clip)
        body = r.json()
        if r.status_code != 200:
            print(f"[{name}] {r.status_code} {body}")
            c.check(f"{name} status", False)
            continue
        session["profile"], session["skipped"] = body["profile"], body["skipped"]
        session["last_question"] = body["next_question"]
        print(
            f"[{name}] {ms:.0f} ms intent={body['intent']} updated={body['updated_keys']}"
            f"{' rejected=' + str(body['rejected_keys']) if body['rejected_keys'] else ''}"
        )
        print(f"    heard: {body['transcript']}")
        print(f"    next:  {body['next_question']}")
        for key, want in expected.items():
            got = value(session["profile"], key)
            c.check(f"{name}: {key}", got == want, f"want {want!r} got {got!r}")
        for key in expected_skips:
            c.check(
                f"{name}: skipped {key}",
                key in session["skipped"],
                f"skipped={session['skipped']}",
            )
        c.check(f"{name}: next question not empty", bool(body["next_question"].strip()))

    print("\n--- final profile ---")
    for key, entry in session["profile"].items():
        flag = "  <0.8 confirm" if entry["confidence"] < 0.8 else ""
        print(
            f"  {key:22} {json.dumps(entry['value'], ensure_ascii=False):45} {entry['confidence']}{flag}"
        )
    print(f"  skipped: {session['skipped']}")
    print(f"  remaining: {body.get('remaining')}  done: {body.get('done')}")

    members = value(session["profile"], "household_members") or []
    got_members = {
        (m["first_name"], m["relationship"], m["date_of_birth"]) for m in members
    }
    c.check("household members", got_members == MEMBERS_EXPECTED, f"got {got_members}")
    street = value(session["profile"], "address_street") or ""
    c.check(
        "address_street",
        "4321" in street and "university" in street.lower(),
        repr(street),
    )
    unit = str(value(session["profile"], "address_unit") or "")
    c.check("address_unit", "7" in unit, repr(unit))
    sources = value(session["profile"], "income_sources") or []
    c.check("income_sources has job", "job" in sources, repr(sources))
    schools = str(value(session["profile"], "children_schools") or "")
    c.check("children_schools", "rosa parks" in schools.lower(), repr(schools))
    c.check(
        "benefits_other filled or skipped",
        value(session["profile"], "benefits_other") is not None
        or "benefits_other" in session["skipped"],
    )
    c.check("done", body.get("done") is True, f"remaining={body.get('remaining')}")


def run_gaps(client: TestClient, c: Checker) -> None:
    print("\n=== Gap fields: empty form field + spoken answer ===")
    session = json.dumps(
        {"language": "es", "selected_form": "sdge_care", "profile": {}}
    )
    for name, text, field, want_status, want_value in GAPS:
        clip = make_clip(name, text)
        r, ms = post(
            client,
            "/voice/answer",
            {"session": session, "field": json.dumps(field)},
            clip,
        )
        body = r.json()
        if r.status_code != 200:
            print(f"[{name}] {r.status_code} {body}")
            c.check(f"{name} status", False)
            continue
        print(
            f"[{name}] {ms:.0f} ms {field['key']}: status={body['status']} value={body['value']!r} "
            f"conf={body['confidence']}"
        )
        print(f"    heard: {body['transcript']}")
        if body["clarification_question"]:
            print(f"    re-ask: {body['clarification_question']}")
        c.check(
            f"{name}: status",
            body["status"] == want_status,
            f"want {want_status} got {body['status']}",
        )
        c.check(
            f"{name}: value",
            body["value"] == want_value,
            f"want {want_value!r} got {body['value']!r}",
        )
        if field.get("sensitive") and body["value"] is not None:
            c.check(
                f"{name}: sensitive capped",
                body["confidence"] < 0.8,
                str(body["confidence"]),
            )
        if want_status == "unclear":
            c.check(f"{name}: re-ask present", bool(body["clarification_question"]))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--only", choices=["onboarding", "gaps"])
    a = p.parse_args()
    client = TestClient(app)
    c = Checker()
    t0 = time.monotonic()
    if a.only in (None, "onboarding"):
        run_onboarding(client, c)
    if a.only in (None, "gaps"):
        run_gaps(client, c)
    print(f"\n{c.passed} passed, {c.failed} failed in {time.monotonic() - t0:.0f} s")
    sys.exit(1 if c.failed else 0)


if __name__ == "__main__":
    main()
