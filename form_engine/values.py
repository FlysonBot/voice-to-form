"""Profile session -> canonical form values for the SDG&E CARE form.

Profile keys read (P3 voice keys first, our drafts as fallback) -> form keys:
  first_name, middle_name, last_name (win) / full_name   -> name
  phone                                                 -> mobile_phone
  home_phone (gap question)                             -> home_phone
  email                                                 -> email, contact_email/contact_mail
  address_street, address_unit, address_city,
    address_zip (win when street+city+zip exist) / address -> address
  sdge_account_number (gap question)                    -> account_number
  household_size (int)                                  -> household_total (adults/children derived)
  household_members (plain list, or {value: list})      -> children, adults
  monthly_income                                        -> annual_income (x12)
  income_sources (comma string, list or dict)           -> inc_*
  benefits_calfresh/medi_cal/wic/ssi/school_meals
    (bool entries) -> pa_calfresh/pa_medicaid/pa_wic/pa_ssi/pa_nslp
  benefits_other (free text), current_benefits (draft)  -> pa_* via aliases (union)
Not read (form does not need): date_of_birth, gender, mailing_address, housing_*,
  school_children, pay_frequency, has_senior/has_disability/has_veteran.
"""

import datetime
import math
import re
import unicodedata
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

# All profile key names live here so renaming is a one-line change.
PROFILE_KEYS = {
    "name": "full_name",
    "phone": "phone",
    "home_phone": "home_phone",
    "email": "email",
    "address": "address",
    "account_number": "sdge_account_number",
    "household_size": "household_size",
    "household_members": "household_members",
    "monthly_income": "monthly_income",
    "income_sources": "income_sources",
    "current_benefits": "current_benefits",
    "first_name": "first_name",
    "middle_name": "middle_name",
    "last_name": "last_name",
    "address_street": "address_street",
    "address_unit": "address_unit",
    "address_city": "address_city",
    "address_zip": "address_zip",
    "benefits_other": "benefits_other",
}

# P3 boolean benefit keys -> form checkbox
BENEFIT_BOOLS = {
    "benefits_calfresh": "pa_calfresh",
    "benefits_medi_cal": "pa_medicaid",
    "benefits_wic": "pa_wic",
    "benefits_ssi": "pa_ssi",
    "benefits_school_meals": "pa_nslp",
}


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "_", str(s).lower()).strip("_")


def _aliases(groups):
    return {_slug(a): target for target, names in groups.items() for a in names}


BENEFIT_MAP = _aliases(
    {
        "pa_calfresh": ["calfresh", "snap"],
        "pa_medicaid": ["medi_cal", "medicaid"],
        "pa_wic": ["wic"],
        "pa_ssi": ["ssi"],
        "pa_nslp": [
            "school_meals",
            "free_reduced_school_meals",
            "nslp",
            "school_lunch",
        ],
        "pa_calworks": ["calworks", "tanf"],
        "pa_liheap": ["liheap"],
        "pa_bia": ["bia", "bia_general_assistance"],
        "pa_tribal_tanf": ["tribal_tanf"],
        "pa_headstart": ["head_start", "headstart"],
    }
)

INCOME_MAP = _aliases(
    {
        "inc_wages": ["job", "jobs", "wages", "self_employment"],
        "inc_rent": ["rent", "rental_income", "royalty", "royalties"],
        "inc_pensions": ["pension", "pensions"],
        "inc_socsec": ["social_security"],
        "inc_ssi_ssdi": ["ssdi", "ssp"],
        "inc_disability": [
            "disability",
            "disability_benefits",
            "workers_compensation",
        ],
        "inc_unemployment": ["unemployment"],
        "inc_scholarships": ["scholarship", "scholarships"],
        "inc_interest": ["interest", "dividends"],
        "inc_support": ["child_support", "spousal_support"],
        "inc_settlements": ["settlement", "settlements"],
        "inc_cash": ["cash", "other"],
    }
)

ALL_PA = sorted(set(BENEFIT_MAP.values()))
ALL_INC = [
    "inc_wages",
    "inc_rent",
    "inc_pensions",
    "inc_socsec",
    "inc_ssi_ssdi",
    "inc_disability",
    "inc_unemployment",
    "inc_scholarships",
    "inc_interest",
    "inc_support",
    "inc_settlements",
    "inc_cash",
]


def _unwrap(item):
    if isinstance(item, dict) and "value" in item:
        return item["value"]
    return item


def _val(session, key):
    try:
        return _unwrap(session["profile"][key])
    except (KeyError, TypeError, IndexError):
        return None


_TRANSLATE = str.maketrans(
    {
        "Đ": "D",
        "đ": "d",
        "Ø": "O",
        "ø": "o",
        "Ł": "L",
        "ł": "l",
        "ß": "ss",
        "\u2018": "'",
        "\u2019": "'",
        "\u201a": "'",
        "\u201b": "'",
        "\u201c": '"',
        "\u201d": '"',
    }
)


def _text(value):
    """str/number -> str; anything else (dict, list, bool, None) -> ''."""
    if isinstance(value, bool):
        return ""
    if isinstance(value, (str, int, float)):
        return str(value).strip()
    return ""


def _ascii(value):
    s = unicodedata.normalize("NFKD", _text(value).translate(_TRANSLATE))
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s.encode("ascii", "ignore").decode("ascii").strip()


def _join(parts, sep):
    return sep.join(t for t in (_text(_unwrap(x)) for x in parts) if t)


def _structured(value, kind):
    value = _unwrap(value)
    if not isinstance(value, dict):
        return value
    if kind == "name":
        return _join([value.get(k) for k in ("first", "middle", "last")], " ")
    first = _join([value.get(k) for k in ("street", "unit", "apt")], " ")
    rest = [value.get(k) for k in ("city", "state", "zip")]
    return _join([first, *rest], ", ")


def _name(value):
    raw = _text(_structured(value, "name")).translate(_TRANSLATE)
    out = _ascii(raw)
    letters = sum(ch.isalpha() for ch in raw)
    if letters and sum(ch.isalpha() for ch in out) * 2 < letters:
        return ""
    return out


def _address_parts(session):
    street, unit, city, zip_ = (
        _text(_val(session, PROFILE_KEYS[k]))
        for k in ("address_street", "address_unit", "address_city", "address_zip")
    )
    if not (street and city and zip_):
        return ""
    first = f"{street} {unit}".strip()
    return f"{first}, {city}, CA {zip_}"


def _phone(value):
    s = _ascii(value)
    digits = "".join(ch for ch in s if ch.isdigit())
    if len(digits) == 11 and digits[0] == "1":
        digits = digits[1:]
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    return s


def _members(session):
    members = _val(session, PROFILE_KEYS["household_members"])
    if members is None and isinstance(session, dict):
        members = _unwrap(session.get("household_members"))
    return members if isinstance(members, list) else []


def _dob(member):
    """Parse a member's date of birth; None when unknown."""
    if not isinstance(member, dict):
        return None
    v = _unwrap(member.get("date_of_birth"))
    if isinstance(v, datetime.datetime):
        return v.date()
    if isinstance(v, datetime.date):
        return v
    if not isinstance(v, str):
        return None
    v = v.strip()
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}([T ].*)?", v):
            return datetime.date.fromisoformat(v[:10])
        if re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}", v):
            return datetime.datetime.strptime(v, "%m/%d/%Y").date()
    except ValueError:
        return None
    return None


def _is_minor(dob, today):
    try:
        eighteenth = dob.replace(year=dob.year + 18)
    except ValueError:  # Feb 29
        eighteenth = dob.replace(year=dob.year + 18, day=28)
    return today < eighteenth


def _number(value):
    if isinstance(value, bool) or value is None:
        return None
    n = None
    if isinstance(value, (int, float)):
        n = float(value)
    elif isinstance(value, str):
        try:
            n = float(value.strip().replace(",", "").lstrip("$"))
        except ValueError:
            return None
    if n is None or not math.isfinite(n):
        return None
    return n


def _labels(value):
    """str, list or {label: truthy} -> list of slugs."""
    value = _unwrap(value)
    if isinstance(value, str):
        items = re.split(r"\s*[,;]\s*|\s+and\s+", value)
    elif isinstance(value, dict):
        items = [k for k, v in value.items() if v]
    elif isinstance(value, list):
        items = [i for i in value if isinstance(i, str)]
    else:
        items = []
    return [_slug(i) for i in items]


def _today():
    try:
        tz = ZoneInfo("America/Los_Angeles")
    except ZoneInfoNotFoundError:
        tz = datetime.timezone(datetime.timedelta(hours=-8))
    return datetime.datetime.now(tz).date()


def build_form_values(session, today=None):
    today = today or _today()
    out = {}

    parts = [
        _val(session, PROFILE_KEYS[k])
        for k in ("first_name", "middle_name", "last_name")
    ]
    name = _name(_join(parts, " ")) or _name(_val(session, PROFILE_KEYS["name"]))
    if name:
        out["name"] = name
    for form_key, pkey, kind in (
        ("email", "email", None),
        ("address", "address", "address"),
        ("account_number", "account_number", None),
    ):
        raw = _val(session, PROFILE_KEYS[pkey])
        if kind:
            raw = _structured(raw, kind)
        if pkey == "address":
            built = _address_parts(session)
            if built:
                raw = built
        text = _ascii(raw)
        if text:
            out[form_key] = text
    for form_key, pkey in (("mobile_phone", "phone"), ("home_phone", "home_phone")):
        text = _phone(_val(session, PROFILE_KEYS[pkey]))
        if text:
            out[form_key] = text

    members = _members(session)
    size = _number(_val(session, PROFILE_KEYS["household_size"]))
    has_self = any(
        isinstance(m, dict)
        and _slug(m.get("relationship") or "") in {"self", "me", "user"}
        for m in members
    )
    total = None
    if size is not None and size >= 1:
        total = int(size)
    elif members:
        total = len(members) if has_self else len(members) + 1
    if total is not None:
        out["household_total"] = str(total)
        dobs = [_dob(m) for m in members]
        expected = len(members) if has_self else len(members) + 1
        if members and all(d is not None for d in dobs) and expected == total:
            children = sum(1 for d in dobs if _is_minor(d, today))
            out["children"] = str(children)
            out["adults"] = str(total - children)

    income = _number(_val(session, PROFILE_KEYS["monthly_income"]))
    if income is not None and income >= 0:
        out["annual_income"] = f"{round(income * 12):,}"

    out["date"] = today.strftime("%m/%d/%Y")

    has_email = "email" in out
    out["contact_email"] = has_email
    out["contact_mail"] = not has_email

    for k in ALL_PA + ALL_INC:
        out[k] = False
    for label in _labels(_val(session, PROFILE_KEYS["current_benefits"])):
        if label in BENEFIT_MAP:
            out[BENEFIT_MAP[label]] = True
    for key, box in BENEFIT_BOOLS.items():
        if _val(session, key) is True:
            out[box] = True
    for label in _labels(_val(session, PROFILE_KEYS["benefits_other"])):
        if label in BENEFIT_MAP:
            out[BENEFIT_MAP[label]] = True
    for label in _labels(_val(session, PROFILE_KEYS["income_sources"])):
        if label in INCOME_MAP:
            out[INCOME_MAP[label]] = True
    return out
