"""Fake responses for ?mock=true. All data is invented (privacy rules: fake data only)."""
from .fields import DERIVED, add_derived, remaining_fields

# A scripted Spanish onboarding: each turn fills a few fields.
_SCRIPT = [
    ("¡Hola! Soy su asistente. No guardamos su información. ¿Cuál es su nombre completo?", {}),
    ("Gracias, María. ¿Cuál es su fecha de nacimiento?", {
        "first_name": "Maria", "last_name": "Lopez", "middle_name": None}),
    ("Perfecto. ¿Cuál es su número de teléfono?", {"date_of_birth": "1988-03-14"}),
    ("¿Cuál es la dirección de su casa?", {"phone": "6195550142"}),
    ("¿Usted renta o es dueña de su casa?", {
        "address_street": "4210 University Ave", "address_unit": "Apt 3", "address_city": "San Diego", "address_zip": "92105"}),
    ("¿Quién vive con usted?", {"housing_status": "rent", "monthly_housing_cost": 1850}),
    ("¿Cuánto gana su hogar al mes, más o menos?", {"household_size": 4, "household_members": [
        {"first_name": "Jose", "relationship": "husband", "date_of_birth": "1985-07-02"},
        {"first_name": "Sofia", "relationship": "daughter", "date_of_birth": "2014-09-21"},
        {"first_name": "Mateo", "relationship": "son", "date_of_birth": "2018-01-30"}]}),
    ("¿Ya recibe CalFresh, Medi-Cal o WIC?", {"monthly_income": 3200, "income_sources": "job", "pay_frequency": "every 2 weeks"}),
    ("¡Listo! Ya tengo todo lo que necesito. Gracias, María.", {
        "benefits_calfresh": False, "benefits_medi_cal": True, "benefits_wic": False,
        "benefits_ssi": False, "benefits_school_meals": True}),
]

_OPTIONAL_SKIP = ["email", "gender", "mailing_address", "school_children", "has_senior", "has_disability", "has_veteran"]


def onboarding_turn(profile: dict, has_audio: bool) -> dict:
    profile = dict(profile)
    step = profile.pop("_mock_step", {"value": 0}).get("value", 0)
    if has_audio:
        step = min(step + 1, len(_SCRIPT) - 1)
    say, fills = _SCRIPT[step]
    for k, v in fills.items():
        if k == "household_members":
            profile[k] = v  # plain list, per CLAUDE.md
        elif v is None:
            profile[k] = {"value": None, "confidence": 1.0, "source": "onboarding_voice", "skipped": True}
        else:
            conf = 0.7 if k in ("last_name", "monthly_income") else 0.95  # a couple of yellow fields for the demo
            profile[k] = {"value": v, "confidence": conf, "source": "onboarding_voice"}
    if step == len(_SCRIPT) - 1:
        for k in _OPTIONAL_SKIP + ["address_unit", "middle_name", "benefits_other"]:
            profile.setdefault(k, {"value": None, "confidence": 1.0, "source": "onboarding_voice", "skipped": True})
    remaining = remaining_fields(profile)
    done = step == len(_SCRIPT) - 1
    profile = add_derived(profile)
    profile["_mock_step"] = {"value": step}
    return {"profile": profile, "transcript": "(mock) respuesta de la usuaria" if has_audio else "",
            "say": say, "done": done, "remaining_fields": [] if done else remaining,
            "updated_fields": list(fills.keys())}


def question(field: str) -> dict:
    q = {"sdge_account_number": "¿Cuál es su número de cuenta de SDG&E? Está arriba, en su factura de luz."}
    return {"field": field, "question": q.get(field, f"¿Me puede decir su {field.replace('_', ' ')}?")}


def answer(field: str) -> dict:
    return {"transcript": "(mock) uno dos tres cuatro...", "intent": "answer", "value": "1234 5678 90",
            "confidence": 0.75, "reply": "Escuché 1, 2, 3, 4, 5, 6, 7, 8, 9, 0. ¿Es correcto?",
            "profile_entry": {"value": "1234 5678 90", "confidence": 0.75, "source": "gap_voice"}}


def recap(profile: dict) -> dict:
    items = []
    for k, e in profile.items():
        if k in DERIVED or k.startswith("_"):
            continue
        if isinstance(e, list):
            e = {"value": e, "confidence": 1.0}
        if not isinstance(e, dict) or e.get("skipped") or e.get("value") in (None, "", []):
            continue
        low = (e.get("confidence") or 0) < 0.8
        items.append({"field": k, "label": k.replace("_", " ").capitalize(), "value": e["value"], "low_confidence": low,
                      "spoken": f"{k.replace('_', ' ')}: {e['value']}." + (" No estoy segura, por favor revíselo." if low else "")})
    intro, outro = "Vamos a revisar su información.", "Si algo está mal, dígamelo. Si todo está bien, toque 'Todo está correcto'."
    return {"intro": intro, "items": items, "outro": outro,
            "script": " ".join([intro] + [i["spoken"] for i in items] + [outro]),
            "needs_confirmation": [i["field"] for i in items if i["low_confidence"]]}


def correct(profile: dict) -> dict:
    profile = dict(profile)
    profile["last_name"] = {"value": "Lopes", "confidence": 1.0, "source": "gap_voice", "user_confirmed": True}
    profile = add_derived(profile)
    return {"transcript": "(mock) mi apellido es con S", "action": "correct", "field": "last_name", "new_value": "Lopes",
            "confidence": 0.95, "reply": "Cambié su apellido a L, O, P, E, S.", "profile": profile}
