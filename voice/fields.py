"""Onboarding profile fields (from CLAUDE.md "Onboarding information").

ALIGN WITH PERSON 1 + 2: these keys are what end up in `profile`, so the
field_map JSONs must use the same names. Change keys here, not in prompts.

type: str | int | money | bool | date | list
"""

LANGUAGES = {
    "en": "English",
    "es": "Spanish",
    "zh": "Chinese (Mandarin, Simplified)",
    "vi": "Vietnamese",
    "tl": "Tagalog",
    "ar": "Arabic",
}

# (key, type, optional, what it means — used to brief Gemini)
ONBOARDING_FIELDS = [
    # 1. Contact (language is picked on the first screen)
    ("phone", "str", False, "phone number, digits only, US format"),
    ("email", "str", True, "email address"),
    # 2. Identity
    ("first_name", "str", False, "legal first name in English/Latin letters"),
    ("middle_name", "str", True, "legal middle name in Latin letters"),
    ("last_name", "str", False, "legal last name in Latin letters"),
    ("date_of_birth", "date", False, "date of birth, format YYYY-MM-DD"),
    ("gender", "str", True, "gender as the user states it"),
    # 3. Address & housing
    ("address_street", "str", False, "home street address, e.g. '4210 University Ave'"),
    ("address_unit", "str", True, "apartment/unit number"),
    ("address_city", "str", False, "city"),
    ("address_zip", "str", False, "5-digit ZIP code"),
    ("mailing_address", "str", True, "full mailing address only if different from home"),
    ("housing_status", "str", False, "'rent' or 'own' (or 'other')"),
    ("monthly_housing_cost", "money", True, "monthly rent or mortgage in USD, number only"),
    # 4. Household
    ("household_size", "int", False, "number of people living in the home, including the user"),
    # Stored as a plain list (not a {value, confidence} entry), per CLAUDE.md:
    # profile.household_members = [{first_name, relationship, date_of_birth}, ...]
    ("household_members", "list", False, "each other person in the home: first name, relationship, date of birth"),
    ("school_children", "str", True, "which school(s)/district the children attend"),
    # 5. Income
    ("monthly_income", "money", False, "total household monthly income in USD before taxes, number only (if a range, use the midpoint and lower confidence)"),
    ("income_sources", "str", False, "comma list from: job, self-employment, social security, disability, child support, other"),
    ("pay_frequency", "str", False, "'weekly', 'every 2 weeks', 'twice a month' or 'monthly'"),
    # 6. Current benefits — yes/no for each (CLAUDE.md), so they map to form checkboxes.
    # One answer like "only Medi-Cal" fills all of them (others = false).
    ("benefits_calfresh", "bool", False, "already enrolled in CalFresh (food stamps / EBT)"),
    ("benefits_medi_cal", "bool", False, "already enrolled in Medi-Cal"),
    ("benefits_wic", "bool", False, "already enrolled in WIC"),
    ("benefits_ssi", "bool", False, "already receives SSI"),
    ("benefits_school_meals", "bool", False, "children already get free/reduced-price school meals"),
    ("benefits_other", "str", True, "any other benefit program they already get, by name"),
    # 7. Situations (optional)
    ("has_senior", "bool", True, "anyone in the household 65 or older"),
    ("has_disability", "bool", True, "anyone in the household with a disability"),
    ("has_veteran", "bool", True, "a veteran in the household"),
]

FIELD_TYPES = {k: t for k, t, _, _ in ONBOARDING_FIELDS}
FIELD_DESC = {k: d for k, _, _, d in ONBOARDING_FIELDS}
FIELD_KEYS = [k for k, *_ in ONBOARDING_FIELDS]

# Never asked by voice, ever (CLAUDE.md privacy/scope rules).
NEVER_ASK = {"immigration_status", "citizenship", "citizenship_status", "alien_number", "a_number", "visa_status"}
# Only asked during gap filling when a form needs them; the user may say "leave it blank".
SENSITIVE_GAP_FIELDS = {"ssn", "social_security_number", "bank_account", "routing_number"}


# Composite keys from the CLAUDE.md example data format. Built from the split
# fields so code using `full_name` / `address` still works. Not asked, not recapped.
DERIVED = {"full_name", "address"}


def value_of(profile: dict, key: str):
    e = profile.get(key)
    if key == "household_members":
        return e if isinstance(e, list) else None
    return e.get("value") if isinstance(e, dict) else None


def is_filled(profile: dict, key: str) -> bool:
    """A field counts as done if it has a value or the user skipped it."""
    if key == "household_members":
        members = profile.get(key)
        # [] is valid when the user lives alone.
        return isinstance(members, list) and (len(members) > 0 or value_of(profile, "household_size") == 1)
    entry = profile.get(key)
    if not isinstance(entry, dict):
        return False
    return entry.get("skipped") is True or entry.get("value") not in (None, "", [])


def add_derived(profile: dict) -> dict:
    """Adds/refreshes `full_name` and `address`. Person 1: call this right before /form/fill
    too, in case the user edited a name or address part on the review screen."""
    p = dict(profile)

    def parts(keys):
        return [(k, p[k]) for k in keys if isinstance(p.get(k), dict) and p[k].get("value") not in (None, "")]

    name = parts(["first_name", "middle_name", "last_name"])
    if value_of(p, "first_name") and value_of(p, "last_name"):
        p["full_name"] = {"value": " ".join(str(e["value"]) for _, e in name),
                          "confidence": min(e.get("confidence") or 0 for _, e in name),
                          "source": p["last_name"].get("source")}
    if value_of(p, "address_street") and value_of(p, "address_city") and value_of(p, "address_zip"):
        street = " ".join(str(e["value"]) for _, e in parts(["address_street", "address_unit"]))
        addr = parts(["address_street", "address_unit", "address_city", "address_zip"])
        p["address"] = {"value": f"{street}, {value_of(p, 'address_city')}, CA {value_of(p, 'address_zip')}",
                        "confidence": min(e.get("confidence") or 0 for _, e in addr),
                        "source": p["address_street"].get("source")}
    return p


def remaining_fields(profile: dict) -> list[str]:
    return [k for k in FIELD_KEYS if not is_filled(profile, k)]


def coerce(key: str, raw: str):
    """Turn Gemini's string value into the right Python type. Returns None if it can't."""
    if raw is None:
        return None
    raw = str(raw).strip()
    if raw == "" or raw.lower() in {"null", "unknown", "n/a"}:
        return None
    t = FIELD_TYPES.get(key, "str")
    try:
        if t == "int":
            return int(float(raw.replace(",", "")))
        if t == "money":
            return round(float(raw.replace(",", "").replace("$", "")), 2)
        if t == "bool":
            return raw.lower() in {"true", "yes", "y", "1", "si", "sí"}
    except ValueError:
        return None
    return raw
