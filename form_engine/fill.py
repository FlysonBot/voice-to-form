"""Glue: session profile -> filled PDF bytes."""

import json
from pathlib import Path

from form_engine.render import merge_onto_form, render_overlay
from form_engine.signature import decode_signature
from form_engine.values import build_form_values

HERE = Path(__file__).parent
FORMS = {"sdge_care": ("sdge_care.layout.json", "sdge_care.pdf")}
_layouts: dict[str, dict] = {}


class UnknownFormError(ValueError):
    pass


def fill_form(session: dict, form_id: str, signature_b64: str | None = None) -> bytes:
    if form_id not in FORMS:
        raise UnknownFormError(f"Unsupported form: {form_id}")
    layout_name, pdf_name = FORMS[form_id]
    if form_id not in _layouts:
        _layouts[form_id] = json.loads((HERE / layout_name).read_text())
    values = build_form_values(session)
    png = decode_signature(signature_b64)
    overlay = render_overlay(_layouts[form_id], values, png)
    return merge_onto_form(str(HERE / pdf_name), overlay)
