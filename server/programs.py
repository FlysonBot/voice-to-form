"""POST /programs/find (Path B): programs the user MAY qualify for, from official sources.

Two Gemini calls, as CLAUDE.md recommends (grounding can't always be combined with a schema):
  1. a Google-Search-grounded call that looks up programs + official URLs for this household
  2. a structured-output call that turns that text into `suggested_programs`
Rules: never guarantee eligibility, never use remembered income limits, official URLs only,
`why` in the user's language. Only the facts needed for matching go to Gemini (no name, phone,
street address). Logs never contain profile values.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any
from urllib.parse import urlparse

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from google.genai import errors, types
from pydantic import BaseModel

from gemini.client import GeminiError, call_audio_json, get_client

log = logging.getLogger("programs")
router = APIRouter()

OFFICIAL_DOMAINS = ("sdge.com", "sandiegounified.org", "sdmts.com")  # plus any *.gov
# Forms the form engine can fill today (see form_engine/*.fields.json)
FILLABLE = {"sdge_care"}

# Profile keys that matter for matching. Everything else (name, phone, street…) stays local.
MATCH_KEYS = (
    "household_size", "household_members", "monthly_income", "income_amount", "income_frequency",
    "income_sources", "housing_status", "monthly_housing_cost", "address_city", "address_zip",
    "benefits_calfresh", "benefits_medi_cal", "benefits_wic", "benefits_ssi", "benefits_school_meals",
    "benefits_other", "has_senior_65_plus", "has_disability", "has_veteran", "children_schools",
)

LANG_NAMES = {"en": "English", "es": "Spanish", "vi": "Vietnamese", "tl": "Tagalog",
              "zh": "Simplified Chinese", "ar": "Arabic", "fr": "French"}


class Program(BaseModel):
    name: str
    why: str
    source_url: str
    is_sdge_care: bool


class ProgramList(BaseModel):
    programs: list[Program]


class FindIn(BaseModel):
    session: dict[str, Any] = {}


MOCK = {
    "suggested_programs": [
        {
            "name": "SDG&E CARE",
            "why": "Un descuento mensual en su factura de SDG&E. Según su hogar e ingresos, podría calificar. SDG&E decide.",
            "source_url": "https://www.sdge.com/care",
            "form_id": "sdge_care",
        }
    ]
}


def _facts(profile: dict) -> dict:
    """Just the values needed for matching, without confidence/source noise."""
    out = {}
    for k in MATCH_KEYS:
        v = (profile.get(k) or {}).get("value") if isinstance(profile.get(k), dict) else None
        if v not in (None, "", []):
            if k == "household_members":  # relationships + ages only, no names
                v = [{"relationship": m.get("relationship"), "date_of_birth": m.get("date_of_birth")}
                     for m in v if isinstance(m, dict)]
            out[k] = v
    return out


def _official(url: str) -> bool:
    """https on a .gov site (incl. .ca.gov) or one of the official program domains."""
    try:
        u = urlparse(url)
    except ValueError:
        return False
    host = (u.hostname or "").lower()
    if u.scheme != "https" or not host:
        return False
    return host.endswith(".gov") or any(host == d or host.endswith("." + d) for d in OFFICIAL_DOMAINS)


def _grounded_search(facts: dict) -> str:
    """Call 1: Google Search grounding → plain-text findings with official URLs."""
    model = os.getenv("GEMINI_MODEL")
    if not model:
        raise GeminiError("GEMINI_MODEL is not set (.env at the repo root)", retryable=False)
    prompt = (
        "A household in San Diego County, California has these facts (JSON):\n"
        f"{json.dumps(facts, ensure_ascii=False)}\n\n"
        "Use Google Search to find up to 5 San Diego County or California assistance programs this "
        "household MAY qualify for, focusing on ones that lower monthly bills (energy, food, transit, "
        "school meals, health). Always check SDG&E CARE. Use the CURRENT income limits published on "
        "the official program pages, not remembered numbers. For each program give: its name, one "
        "or two sentences on why this household may qualify (mention the rule, e.g. income limit for "
        "their household size, or already receiving a qualifying benefit), and the official page URL. "
        "Only use official sources: .gov, .ca.gov, sdge.com, sandiegounified.org, sdmts.com. "
        "If the facts are not enough to judge a program, say what is unknown. Never say they definitely qualify."
    )
    client = get_client()
    t0 = time.monotonic()
    try:
        resp = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())], temperature=0.2
            ),
        )
    except errors.APIError as e:
        log.warning("programs grounded call failed code=%s", e.code)
        raise GeminiError(f"Gemini API error {e.code}", e.code in {429, 500, 502, 503, 504}) from None
    log.info("programs grounded ok model=%s ms=%d", model, (time.monotonic() - t0) * 1000)

    text = resp.text or ""
    # Grounding sources (titles are usually the site's domain) help the second call pick real URLs
    try:
        chunks = resp.candidates[0].grounding_metadata.grounding_chunks or []
        sources = sorted({c.web.title for c in chunks if c.web and c.web.title})
        if sources:
            text += "\n\nSites consulted: " + ", ".join(sources)
    except (AttributeError, IndexError, TypeError):
        pass
    return text


def find_programs(session: dict) -> list[dict]:
    lang = session.get("language") or "es"
    lang_name = LANG_NAMES.get(lang, lang)
    facts = _facts(session.get("profile") or {})
    findings = _grounded_search(facts)

    # Call 2: structure it, with "why" written for the user in their language
    out: ProgramList = call_audio_json(
        audio=None,
        mime_type=None,
        system_instruction=(
            "You turn research notes into a short list of benefit programs for a person who is not "
            f"comfortable with English. Write every `why` in {lang_name}, in plain, warm, simple words, "
            "2 sentences max. Always say they MAY qualify and that the program decides; never promise. "
            "Keep program names in their official English form. source_url must be the official page "
            "URL from the notes (https, on .gov, .ca.gov, sdge.com, sandiegounified.org or sdmts.com). "
            "Set is_sdge_care=true only for the SDG&E CARE program."
        ),
        prompt=f"Research notes:\n{findings}\n\nReturn at most 5 programs, most useful first.",
        schema=ProgramList,
    )

    programs = []
    for p in out.programs:
        url = p.source_url.strip()
        if p.is_sdge_care and not _official(url):
            url = "https://www.sdge.com/care"  # CARE's official page; never drop our fillable form
        if not _official(url):
            log.info("programs: dropped a result with a non-official URL")
            continue
        form_id = "sdge_care" if p.is_sdge_care else None
        programs.append({"name": p.name.strip(), "why": p.why.strip(), "source_url": url,
                         "form_id": form_id if form_id in FILLABLE else None})
    # Fillable forms first so the demo path is one tap away
    programs.sort(key=lambda p: p["form_id"] is None)
    return programs


@router.post("/programs/find")
def programs_find(body: FindIn, mock: bool = False):
    if mock:
        return MOCK
    try:
        return {"suggested_programs": find_programs(body.session)}
    except GeminiError as e:
        return JSONResponse(status_code=502, content={"error": str(e), "retryable": e.retryable})
    except Exception as e:  # noqa: BLE001  (never crash the flow)
        log.error("programs_find failed: %s", type(e).__name__)
        return JSONResponse(status_code=500, content={"error": "Something went wrong. Please try again.",
                                                      "retryable": True})
