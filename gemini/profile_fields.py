"""Profile key catalog + pure helpers for typing, merging and tracking profile fields.

This file is the single source of truth for onboarding profile keys. Person 1's
`forms/<form_id>.field_map.json` maps PDF fields to these keys.

Never add SSN, bank/utility account numbers or immigration status here: those are
gap-only (or never asked) per CLAUDE.md.
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class FieldSpec:
    type: str  # string|name|int|number|bool|date|phone|zip|email|enum|list_enum|members
    section: str
    optional: bool
    description: str
    options: tuple[str, ...] | None = None
    computed: bool = False  # filled by the backend, never asked or extracted


INCOME_SOURCES = (
    "job",
    "self_employment",
    "social_security",
    "disability_benefits",
    "child_support",
    "unemployment",
    "other",
)
INCOME_FREQUENCIES = ("weekly", "biweekly", "semimonthly", "monthly", "yearly")
RELATIONSHIPS = (
    "spouse",
    "partner",
    "child",
    "stepchild",
    "parent",
    "sibling",
    "grandparent",
    "grandchild",
    "other_relative",
    "roommate",
    "other",
)

ONBOARDING_FIELDS: dict[str, FieldSpec] = {
    # 1. contact
    "phone": FieldSpec("phone", "contact", False, "Phone number"),
    "email": FieldSpec("email", "contact", True, "Email address"),
    # 2. identity
    "first_name": FieldSpec(
        "name", "identity", False, "Legal first name, in English letters"
    ),
    "middle_name": FieldSpec(
        "name", "identity", True, "Legal middle name, in English letters"
    ),
    "last_name": FieldSpec(
        "name", "identity", False, "Legal last name(s), in English letters"
    ),
    "date_of_birth": FieldSpec("date", "identity", False, "User's date of birth"),
    "gender": FieldSpec(
        "enum",
        "identity",
        True,
        "Gender",
        ("female", "male", "nonbinary", "prefer_not_to_say"),
    ),
    # 3. address & housing
    "address_street": FieldSpec(
        "string", "address", False, "Home street address (number and street)"
    ),
    "address_unit": FieldSpec("string", "address", True, "Apartment or unit number"),
    "address_city": FieldSpec("string", "address", False, "Home city"),
    "address_zip": FieldSpec("zip", "address", False, "Home ZIP code"),
    "mailing_address": FieldSpec(
        "string",
        "address",
        True,
        "Full mailing address if different from home; 'same_as_home' if the same",
    ),
    "housing_status": FieldSpec(
        "enum",
        "address",
        False,
        "Do they rent or own their home",
        ("rent", "own", "other"),
    ),
    "monthly_housing_cost": FieldSpec(
        "number", "address", True, "Monthly rent or mortgage in dollars"
    ),
    # 4. household
    "household_size": FieldSpec(
        "int",
        "household",
        False,
        "Number of people living in the home, including the user",
    ),
    "household_members": FieldSpec(
        "members",
        "household",
        False,
        "Each other person in the home: first name, relationship, date of birth",
    ),
    "children_schools": FieldSpec(
        "string", "household", True, "School and district of each child in school"
    ),
    # 5. income
    "income_amount": FieldSpec(
        "number",
        "income",
        False,
        "Total household income amount in dollars, per the stated frequency",
    ),
    "income_frequency": FieldSpec(
        "enum",
        "income",
        False,
        "How often that income amount is received",
        INCOME_FREQUENCIES,
    ),
    "income_sources": FieldSpec(
        "list_enum",
        "income",
        False,
        "Where the household income comes from",
        INCOME_SOURCES,
    ),
    "monthly_income": FieldSpec(
        "number", "income", False, "Computed monthly household income", computed=True
    ),
    # 6. current benefits
    "benefits_calfresh": FieldSpec(
        "bool", "benefits", False, "Anyone in household gets CalFresh (food stamps/EBT)"
    ),
    "benefits_medi_cal": FieldSpec(
        "bool", "benefits", False, "Anyone in household has Medi-Cal"
    ),
    "benefits_wic": FieldSpec(
        "bool", "benefits", False, "Anyone in household gets WIC"
    ),
    "benefits_ssi": FieldSpec(
        "bool", "benefits", False, "Anyone in household gets SSI"
    ),
    "benefits_school_meals": FieldSpec(
        "bool", "benefits", False, "Children get free or reduced-price school meals"
    ),
    "benefits_other": FieldSpec(
        "string", "benefits", True, "Any other public benefits received"
    ),
    # 7. situations that unlock programs
    "has_senior_65_plus": FieldSpec(
        "bool", "situations", True, "Anyone in household is 65 or older"
    ),
    "has_disability": FieldSpec(
        "bool", "situations", True, "Anyone in household has a disability"
    ),
    "has_veteran": FieldSpec(
        "bool", "situations", True, "A veteran lives in the household"
    ),
}

# Keys Gemini may put in `updates` (members are returned separately; computed keys never).
EXTRACTABLE_KEYS = [
    k for k, s in ONBOARDING_FIELDS.items() if not s.computed and s.type != "members"
]

_YES = {"yes", "y", "true", "si", "sí", "1"}
_NO = {"no", "n", "false", "0", "none"}
_MONTHLY_FACTOR = {
    "weekly": 52 / 12,
    "biweekly": 26 / 12,
    "semimonthly": 2.0,
    "monthly": 1.0,
    "yearly": 1 / 12,
}


def _digits(s: str) -> str:
    return re.sub(r"\D", "", s)


def _norm_option(s: str) -> str:
    return re.sub(r"[\s\-]+", "_", s.strip().lower())


def coerce_value(field_type: str, raw, options=None):
    """Turn Gemini's string value into a typed, normalized value. Returns None if unusable."""
    if raw is None:
        return None
    s = str(raw).strip()
    if not s or (field_type != "bool" and s.lower() in {"null", "none", "n/a"}):
        return None
    try:
        if field_type == "string":
            return re.sub(r"\s+", " ", s)
        if field_type == "name":
            s = re.sub(r"\s+", " ", s)
            # Only fix casing when it's clearly wrong; keep "McDonald" as given.
            if s.islower() or s.isupper():
                s = " ".join(w[:1].upper() + w[1:].lower() for w in s.split(" "))
            return s
        if field_type == "int":
            d = _digits(s)
            return int(d) if d else None
        if field_type == "number":
            n = float(re.sub(r"[^\d.\-]", "", s))
            return int(n) if n.is_integer() else round(n, 2)
        if field_type == "bool":
            low = s.lower()
            if low in _YES:
                return True
            if low in _NO:
                return False
            return None
        if field_type == "date":
            return date.fromisoformat(s[:10]).isoformat()
        if field_type == "phone":
            d = _digits(s)
            if len(d) == 11 and d.startswith("1"):
                d = d[1:]
            return d if len(d) == 10 else None
        if field_type == "zip":
            d = _digits(s)
            return d[:5] if len(d) >= 5 else None
        if field_type == "email":
            s = s.replace(" ", "").lower()
            return s if re.fullmatch(r"[^@]+@[^@]+\.[^@]+", s) else None
        if field_type == "digits":
            d = _digits(s)
            return d or None
        if field_type == "enum":
            v = _norm_option(s)
            if not options:
                return v
            return v if v in options else None
        if field_type == "list_enum":
            parts = [_norm_option(p) for p in re.split(r"[,;]", s) if p.strip()]
            vals = [p for p in parts if not options or p in options]
            return list(dict.fromkeys(vals)) or None
    except (ValueError, TypeError):
        return None
    return s


def coerce_members(members) -> list[dict]:
    out = []
    for m in members or []:
        m = m if isinstance(m, dict) else m.model_dump(mode="json")
        rel = coerce_value("enum", m.get("relationship"), RELATIONSHIPS) or "other"
        out.append(
            {
                "first_name": coerce_value("name", m.get("first_name")),
                "relationship": rel,
                "date_of_birth": coerce_value("date", m.get("date_of_birth")),
            }
        )
    return out


def _value(profile: dict, key: str):
    entry = profile.get(key)
    return entry.get("value") if isinstance(entry, dict) else None


def _set(profile: dict, key: str, value, confidence: float, source: str) -> None:
    profile[key] = {
        "value": value,
        "confidence": round(float(confidence), 2),
        "source": source,
    }


def merge_updates(
    profile: dict, updates: list[dict], source: str, overwrite: bool = False
):
    """Merge `[{key, value, confidence}]` (value already typed) into a copy of profile.

    Doesn't replace an existing value that has higher confidence unless `overwrite`
    (used for user corrections). Returns (new_profile, updated_keys).
    """
    new = copy.deepcopy(profile or {})
    updated = []
    for u in updates:
        key, value = u["key"], u["value"]
        if key not in ONBOARDING_FIELDS or value is None:
            continue
        conf = max(0.0, min(1.0, float(u.get("confidence", 0))))
        existing = new.get(key) or {}
        if (
            not overwrite
            and existing.get("value") is not None
            and existing.get("confidence", 0) > conf
        ):
            continue
        _set(new, key, value, conf, source)
        updated.append(key)
    if {"income_amount", "income_frequency"} & set(updated):
        _recompute_monthly_income(new)
    return new, updated


def compute_monthly_income(amount, frequency):
    factor = _MONTHLY_FACTOR.get(frequency or "")
    if amount is None or factor is None:
        return None
    return round(float(amount) * factor, 2)


def _recompute_monthly_income(profile: dict) -> None:
    monthly = compute_monthly_income(
        _value(profile, "income_amount"), _value(profile, "income_frequency")
    )
    if monthly is None:
        return
    conf = min(
        profile["income_amount"]["confidence"],
        profile["income_frequency"]["confidence"],
    )
    _set(profile, "monthly_income", monthly, conf, profile["income_amount"]["source"])


def members_complete(profile: dict) -> bool:
    size = _value(profile, "household_size")
    members = _value(profile, "household_members")
    if size == 1:
        return True
    if not isinstance(size, int) or not isinstance(members, list):
        return False
    return len(members) >= size - 1 and all(
        m.get("first_name") and m.get("date_of_birth") for m in members
    )


def remaining_fields(profile: dict, skipped) -> list[str]:
    """Fields still to ask about, in catalog (section) order."""
    skipped = set(skipped or [])
    out = []
    for key, spec in ONBOARDING_FIELDS.items():
        if spec.computed or key in skipped:
            continue
        if spec.type == "members":
            if not members_complete(profile):
                out.append(key)
        elif _value(profile, key) is None:
            out.append(key)
    return out
