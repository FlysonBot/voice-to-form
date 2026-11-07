import pytest

from gemini.profile_fields import (
    EXTRACTABLE_KEYS,
    ONBOARDING_FIELDS,
    coerce_members,
    coerce_value,
    compute_monthly_income,
    members_complete,
    merge_updates,
    remaining_fields,
)


@pytest.mark.parametrize(
    "ftype,raw,options,expected",
    [
        ("int", "4", None, 4),
        ("int", "four", None, None),
        ("number", "$1,850.50", None, 1850.5),
        ("number", "2000", None, 2000),
        ("bool", "yes", None, True),
        ("bool", "sí", None, True),
        ("bool", "no", None, False),
        ("bool", "maybe", None, None),
        ("date", "1988-03-14", None, "1988-03-14"),
        ("date", "1988-02-31", None, None),
        ("date", "March 14", None, None),
        ("phone", "(619) 555-0142", None, "6195550142"),
        ("phone", "1-619-555-0142", None, "6195550142"),
        ("phone", "555-0142", None, None),
        ("zip", "92105-1234", None, "92105"),
        ("zip", "921", None, None),
        ("email", "Maria.Lopez @Example.com", None, "maria.lopez@example.com"),
        ("email", "maria at example", None, None),
        ("name", "MARIA JOSE", None, "Maria Jose"),
        ("name", "McDonald", None, "McDonald"),
        ("enum", "Rent", ("rent", "own", "other"), "rent"),
        ("enum", "lease", ("rent", "own", "other"), None),
        (
            "list_enum",
            "job, social security, lottery",
            ("job", "social_security"),
            ["job", "social_security"],
        ),
        ("digits", "0123 4567-890", None, "01234567890"),
        ("string", "  4321   University Ave ", None, "4321 University Ave"),
        ("string", "null", None, None),
        ("string", "", None, None),
    ],
)
def test_coerce_value(ftype, raw, options, expected):
    assert coerce_value(ftype, raw, options) == expected


def test_catalog_never_has_sensitive_keys():
    for bad in (
        "ssn",
        "social_security_number",
        "immigration_status",
        "citizenship",
        "bank_account",
    ):
        assert bad not in ONBOARDING_FIELDS
    assert "monthly_income" not in EXTRACTABLE_KEYS
    assert "household_members" not in EXTRACTABLE_KEYS


def test_merge_keeps_higher_confidence_unless_overwrite():
    profile = {
        "address_zip": {"value": "92105", "confidence": 0.95, "source": "id_photo"}
    }
    p2, upd = merge_updates(
        profile,
        [{"key": "address_zip", "value": "92115", "confidence": 0.6}],
        "onboarding_voice",
    )
    assert upd == [] and p2["address_zip"]["value"] == "92105"
    p3, upd = merge_updates(
        profile,
        [{"key": "address_zip", "value": "92115", "confidence": 0.95}],
        "onboarding_voice",
        overwrite=True,
    )
    assert upd == ["address_zip"]
    assert p3["address_zip"] == {
        "value": "92115",
        "confidence": 0.95,
        "source": "onboarding_voice",
    }
    assert profile["address_zip"]["value"] == "92105"  # input not mutated


def test_merge_ignores_unknown_keys_and_none():
    p, upd = merge_updates(
        {},
        [
            {"key": "ssn", "value": "123", "confidence": 1},
            {"key": "phone", "value": None, "confidence": 1},
        ],
        "onboarding_voice",
    )
    assert p == {} and upd == []


@pytest.mark.parametrize(
    "amount,freq,expected",
    [
        (500, "weekly", 2166.67),
        (1000, "biweekly", 2166.67),
        (1000, "semimonthly", 2000.0),
        (2400, "monthly", 2400.0),
        (36000, "yearly", 3000.0),
        (500, None, None),
    ],
)
def test_compute_monthly_income(amount, freq, expected):
    assert compute_monthly_income(amount, freq) == expected


def test_monthly_income_computed_on_merge():
    p, _ = merge_updates(
        {},
        [
            {"key": "income_amount", "value": 1000, "confidence": 0.9},
            {"key": "income_frequency", "value": "biweekly", "confidence": 0.7},
        ],
        "onboarding_voice",
    )
    assert p["monthly_income"] == {
        "value": 2166.67,
        "confidence": 0.7,
        "source": "onboarding_voice",
    }


def test_members_complete():
    assert members_complete({"household_size": {"value": 1}})
    assert not members_complete({"household_size": {"value": 3}})
    members = coerce_members(
        [
            {
                "first_name": "jose",
                "relationship": "Spouse",
                "date_of_birth": "1985-01-02",
            },
            {"first_name": "Ana", "relationship": "daughter", "date_of_birth": None},
        ]
    )
    assert members[1]["relationship"] == "other"  # not in enum → other
    profile = {"household_size": {"value": 3}, "household_members": {"value": members}}
    assert not members_complete(profile)  # Ana has no DOB
    members[1]["date_of_birth"] = "2015-06-01"
    assert members_complete(profile)


def test_remaining_fields_order_and_skips():
    rem = remaining_fields({}, [])
    assert rem[0] == "phone" and "monthly_income" not in rem
    rem = remaining_fields({"phone": {"value": "6195550142"}}, ["email"])
    assert rem[0] == "first_name"
    assert "household_members" not in remaining_fields(
        {"household_size": {"value": 1}}, []
    )


def test_names_and_address_are_split_keys():
    for combined in ("full_name", "name", "address"):
        assert combined not in ONBOARDING_FIELDS
    for key in (
        "first_name",
        "middle_name",
        "last_name",
        "address_street",
        "address_unit",
        "address_city",
        "address_zip",
    ):
        assert key in ONBOARDING_FIELDS
