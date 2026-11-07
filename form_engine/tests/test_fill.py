import base64
import io
import json
from pathlib import Path

import pytest
from pypdf import PdfReader

from form_engine.fill import UnknownFormError, fill_form

FIX = Path(__file__).parent.parent / "fixtures"
SESSION = json.loads((FIX / "mock_session.json").read_text())
SIG = base64.b64encode((FIX / "test_signature.png").read_bytes()).decode()


def _text(pdf):
    r = PdfReader(io.BytesIO(pdf))
    assert len(r.pages) == 1
    return r.pages[0].extract_text()


def test_fill_with_signature():
    pdf = fill_form(SESSION, "sdge_care", SIG)
    assert pdf.startswith(b"%PDF")
    text = _text(pdf)
    assert "Maria Lopez" in text
    # annual income is drawn one digit per box, so check the digits in order
    digits = "".join(ch for ch in text if ch.isdigit())
    assert "38400" in digits


def test_fill_without_signature():
    pdf = fill_form(SESSION, "sdge_care", None)
    assert pdf.startswith(b"%PDF")
    assert "Maria Lopez" in _text(pdf)


def test_unknown_form():
    with pytest.raises(UnknownFormError):
        fill_form(SESSION, "visa_form")


def test_bad_signature():
    with pytest.raises(ValueError):
        fill_form(SESSION, "sdge_care", "not-an-image!!")
