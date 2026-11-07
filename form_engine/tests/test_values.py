import datetime

from form_engine.values import build_form_values

TODAY = datetime.date(2026, 11, 7)


def p(v):
    return {"value": v, "confidence": 1.0, "source": "onboarding_voice"}


def full():
    return {
        "language": "es",
        "profile": {
            "full_name": p("María López"),
            "phone": p("6195550123"),
            "email": p("maria@example.com"),
            "address": p("123 Main St, San Diego, CA 92105"),
            "sdge_account_number": p("0001234567"),
            "household_size": p(4),
            "household_members": p(
                [
                    {
                        "first_name": "A",
                        "relationship": "child",
                        "date_of_birth": "2015-05-01",
                    },
                    {
                        "first_name": "B",
                        "relationship": "spouse",
                        "date_of_birth": "1985-01-01",
                    },
                ]
            ),
            "monthly_income": p(3200),
            "income_sources": p(["job", "child_support"]),
            "current_benefits": p(["CalFresh", "medi_cal"]),
        },
    }


def test_full():
    v = build_form_values(full(), TODAY)
    assert v["name"] == "Maria Lopez"
    assert v["mobile_phone"] == "(619) 555-0123"
    assert v["household_total"] == "4"
    assert "children" not in v and "adults" not in v  # 2 members + user != 4
    assert v["annual_income"] == "38,400"
    assert v["date"] == "11/07/2026"
    assert v["contact_email"] and not v["contact_mail"]
    assert v["pa_calfresh"] and v["pa_medicaid"] and not v["pa_wic"]
    assert v["inc_wages"] and v["inc_support"] and not v["inc_rent"]
    assert "signature" not in v


def test_empty():
    for s in ({}, {"profile": {}}, {"profile": {"full_name": None}}):
        v = build_form_values(s, TODAY)
        assert v["date"] == "11/07/2026"
        assert v["contact_mail"] is True and v["contact_email"] is False
        for k in ("name", "address", "annual_income", "household_total", "email"):
            assert k not in v
        assert not any(
            val is True for k, val in v.items() if k.startswith(("pa_", "inc_"))
        )


def test_phone_formats():
    s = {"profile": {"phone": p("(619) 555-0123"), "home_phone": p("555-1234")}}
    v = build_form_values(s, TODAY)
    assert v["mobile_phone"] == "(619) 555-0123"
    assert v["home_phone"] == "555-1234"


def test_children_boundary():
    def kids(dob):
        s = {
            "profile": {
                "household_size": p(2),
                "household_members": [{"date_of_birth": dob}],
            }
        }
        return build_form_values(s, TODAY)

    assert kids("2008-11-08")["children"] == "1"  # turns 18 tomorrow
    assert kids("2008-11-07")["children"] == "0"  # turns 18 today
    assert "children" not in kids("garbage")


def test_counts_do_not_guess():
    members = [{"date_of_birth": "2020-01-01"}] * 3
    s = {"profile": {"household_size": p(2), "household_members": members}}
    v = build_form_values(s, TODAY)
    assert v["household_total"] == "2" and "adults" not in v
    s = {"profile": {"household_size": p(4), "household_members": members}}
    v = build_form_values(s, TODAY)
    assert (v["children"], v["adults"]) == ("3", "1")


def test_self_member():
    m = [
        {"relationship": "self", "date_of_birth": "1990-01-01"},
        {"relationship": "child", "date_of_birth": "2015-01-01"},
    ]
    v = build_form_values(
        {"profile": {"household_size": p(2), "household_members": m}}, TODAY
    )
    assert (v["children"], v["adults"]) == ("1", "1")
    v = build_form_values({"profile": {"household_members": m}}, TODAY)
    assert v["household_total"] == "2"


def test_dob_formats():
    def ch(dob):
        m = [{"date_of_birth": dob}]
        s = {"profile": {"household_members": p(m)}}
        return build_form_values(s, TODAY).get("children")

    assert ch("2018-05-01T00:00:00") == "1"
    assert ch("2018-05-01T00:00:00Z") == "1"
    assert ch("05/01/2018") == "1"
    assert ch({"value": "1980-05-01"}) == "0"
    assert ch("May 1 2018") is None
    assert ch(None) is None


def test_default_today_is_date():
    from form_engine.values import _today

    assert isinstance(_today(), datetime.date)
    assert build_form_values({})["date"]


def test_label_normalization():
    s = {
        "profile": {
            "current_benefits": p(["SNAP", "Medi-Cal", "Free/Reduced School Meals"]),
            "income_sources": p({"Self Employment": True, "Child-Support": 1, "x": 0}),
        }
    }
    v = build_form_values(s, TODAY)
    assert v["pa_calfresh"] and v["pa_medicaid"] and v["pa_nslp"]
    assert v["inc_wages"] and v["inc_support"]
    s = {
        "profile": {
            "current_benefits": p("Head Start"),
            "income_sources": p("Pensions"),
        }
    }
    v = build_form_values(s, TODAY)
    assert v["pa_headstart"] and v["inc_pensions"]
    s = {
        "profile": {
            "current_benefits": p({"BIA General Assistance": True, "tribal-tanf": True})
        }
    }
    v = build_form_values(s, TODAY)
    assert v["pa_bia"] and v["pa_tribal_tanf"]
    s = {
        "profile": {
            "income_sources": p(["Workers Compensation", "Royalty", "Dividends"])
        }
    }
    v = build_form_values(s, TODAY)
    assert v["inc_disability"] and v["inc_rent"] and v["inc_interest"]


def test_structured_values():
    s = {
        "profile": {
            "full_name": p({"first": "Ana", "middle": "B", "last": "Cruz"}),
            "address": p(
                {
                    "street": "1 Main St",
                    "unit": "Apt 2",
                    "city": "San Diego",
                    "state": "CA",
                    "zip": 92105,
                }
            ),
            "email": p(["a@b.c"]),
        }
    }
    v = build_form_values(s, TODAY)
    assert v["name"] == "Ana B Cruz"
    assert v["address"] == "1 Main St Apt 2, San Diego, CA, 92105"
    assert "email" not in v and v["contact_mail"]


def test_phone_country_code():
    for raw in ("+1 619 555 0123", "16195550123", "1-619-555-0123"):
        v = build_form_values({"profile": {"phone": p(raw)}}, TODAY)
        assert v["mobile_phone"] == "(619) 555-0123"


def test_numbers_rejected():
    for bad in (-5, float("inf"), float("nan"), "-100"):
        v = build_form_values({"profile": {"monthly_income": p(bad)}}, TODAY)
        assert "annual_income" not in v
    v = build_form_values({"profile": {"household_size": p(0)}}, TODAY)
    assert "household_total" not in v


def test_names():
    def nm(x):
        return build_form_values({"profile": {"full_name": p(x)}}, TODAY).get("name")

    assert nm("Đặng Łukasz Øster Straße") == "Dang Lukasz Oster Strasse"
    assert nm("O\u2019Brien") == "O'Brien"
    assert nm("李小龍") is None
    assert nm("李小龍 Lee") == "Lee"


def test_members_locations():
    m = [{"first_name": "A", "date_of_birth": "2015-01-01"}]
    for s in (
        {"profile": {"household_members": m}},
        {"profile": {"household_members": p(m)}},
        {"profile": {}, "household_members": m},
    ):
        v = build_form_values(s, TODAY)
        assert v["household_total"] == "2"
        assert v["children"] == "1"
        assert v["adults"] == "1"


def test_income():
    assert (
        build_form_values({"profile": {"monthly_income": p("1,000")}}, TODAY)[
            "annual_income"
        ]
        == "12,000"
    )
    assert "annual_income" not in build_form_values(
        {"profile": {"monthly_income": p("2000-3000")}}, TODAY
    )


def test_unknown_ignored():
    s = {
        "profile": {
            "current_benefits": p(["bogus", "WIC"]),
            "income_sources": p(["bogus", "Pension"]),
        }
    }
    v = build_form_values(s, TODAY)
    assert v["pa_wic"] and v["inc_pensions"]
    assert sum(1 for k, x in v.items() if k.startswith(("pa_", "inc_")) and x) == 2


def p3(**kw):
    return {"language": "es", "profile": {k: p(v) for k, v in kw.items()}}


def test_p3_name_parts():
    v = build_form_values(
        p3(first_name="Maria", middle_name="", last_name="Lopez"), TODAY
    )
    assert v["name"] == "Maria Lopez"
    s = p3(first_name="Ana", middle_name="Luz", last_name="Ruiz", full_name="Old Name")
    assert build_form_values(s, TODAY)["name"] == "Ana Luz Ruiz"
    assert build_form_values(p3(full_name="Old Name"), TODAY)["name"] == "Old Name"


def test_p3_address_parts():
    s = p3(
        address_street="4210 University Ave",
        address_unit="Apt 2",
        address_city="San Diego",
        address_zip="92105",
    )
    assert (
        build_form_values(s, TODAY)["address"]
        == "4210 University Ave Apt 2, San Diego, CA 92105"
    )
    s = p3(
        address_street="4210 University Ave",
        address_unit="",
        address_city="San Diego",
        address_zip="92105",
    )
    assert (
        build_form_values(s, TODAY)["address"]
        == "4210 University Ave, San Diego, CA 92105"
    )
    assert "address" not in build_form_values(
        p3(address_street="1 A St", address_city="X"), TODAY
    )
    s = p3(address_street="1 A St", address="9 Old Rd, San Diego, CA 92101")
    assert build_form_values(s, TODAY)["address"] == "9 Old Rd, San Diego, CA 92101"


def test_p3_benefits():
    s = p3(
        benefits_calfresh=True,
        benefits_medi_cal=True,
        benefits_wic=False,
        benefits_ssi=True,
        benefits_school_meals=True,
        benefits_other="LIHEAP and CalWORKs, bogus",
    )
    s["profile"]["current_benefits"] = p(["wic"])
    v = build_form_values(s, TODAY)
    on = {k for k, x in v.items() if k.startswith("pa_") and x}
    assert on == {
        "pa_calfresh",
        "pa_medicaid",
        "pa_ssi",
        "pa_nslp",
        "pa_liheap",
        "pa_calworks",
        "pa_wic",
    }


def test_p3_income_sources_string():
    v = build_form_values(
        p3(income_sources="job, self-employment, social security and child support"),
        TODAY,
    )
    on = {k for k, x in v.items() if k.startswith("inc_") and x}
    assert on == {"inc_wages", "inc_socsec", "inc_support"}
    assert not build_form_values(p3(income_sources="other stuff"), TODAY)["inc_wages"]


def test_p3_gap_keys_and_members():
    s = p3(sdge_account_number="0001234567", home_phone="6195550000", household_size=3)
    s["profile"]["household_members"] = [
        {"first_name": "A", "relationship": "child", "date_of_birth": "2015-05-01"},
        {"first_name": "B", "relationship": "spouse", "date_of_birth": "1985-01-01"},
    ]
    v = build_form_values(s, TODAY)
    assert v["account_number"] == "0001234567"
    assert v["home_phone"] == "(619) 555-0000"
    assert (v["household_total"], v["children"], v["adults"]) == ("3", "1", "2")
