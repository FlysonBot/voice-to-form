import base64
import datetime
import io
import json
import shutil
import subprocess
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image, ImageChops
from pypdf import PdfReader

from form_engine import routes

HERE = Path(__file__).parent.parent
FIX = HERE / "fixtures"
SESSION = json.loads((FIX / "mock_session.json").read_text())
SIG = base64.b64encode((FIX / "test_signature.png").read_bytes()).decode()
LAYOUT = json.loads((HERE / "sdge_care.layout.json").read_text())

app = FastAPI()
app.include_router(routes.router)
client = TestClient(app)


def _post(session, sig=SIG, url="/form/fill"):
    return client.post(
        url, json={"session": session, "form_id": "sdge_care", "signature_png": sig}
    )


def _text(pdf):
    r = PdfReader(io.BytesIO(pdf))
    assert len(r.pages) == 1
    return r.pages[0].extract_text()


def _digits(t: str) -> str:
    return "".join(ch for ch in t if ch.isdigit())


def _render(pdf: bytes, name: str, scratch: Path, dpi: int = 110) -> Image.Image:
    if not shutil.which("pdftoppm"):
        pytest.skip("pdftoppm not installed")
    src = scratch / f"{name}.pdf"
    src.write_bytes(pdf)
    subprocess.run(
        [
            "pdftoppm",
            "-r",
            str(dpi),
            "-png",
            "-singlefile",
            str(src),
            str(scratch / name),
        ],
        check=True,
    )
    return Image.open(scratch / f"{name}.png").convert("L")


def _ink(img: Image.Image, blank: Image.Image, key: str, dpi: int = 110) -> int:
    """Count pixels in the checkbox area that are darker than in the blank form."""
    s = dpi / 72
    f = LAYOUT["fields"][key]
    x0, x1 = f["x"] * s, (f["x"] + f["size"]) * s
    y1, y0 = (792 - f["y"]) * s, (792 - f["y"] - f["size"]) * s
    box = (int(x0) - 1, int(y0) - 1, int(x1) + 2, int(y1) + 2)
    a, b = img.crop(box), blank.crop(box)
    diff = ImageChops.subtract(b, a)
    return sum(diff.histogram()[61:])


def test_fill_full_session():
    r = _post(SESSION)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF")
    text = _text(r.content)
    for expected in (
        "Maria Lopez",
        "123 Fake St Apt 4",
        "123456789012",
        datetime.datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%m/%d/%Y"),
    ):
        assert expected in text
    assert "38400" in _digits(text)


def test_fill_mock_mode():
    r = _post({}, sig=None, url="/form/fill?mock=true")
    assert r.status_code == 200
    text = _text(r.content)
    assert "Maria Lopez" in text and "38400" in _digits(text)


def test_fill_sparse_session(tmp_path):
    sparse = {"language": "es", "profile": {"full_name": {"value": "Maria Lopez"}}}
    r = _post(sparse, sig=None)
    assert r.status_code == 200
    assert "Maria Lopez" in _text(r.content)
    assert "38400" not in _digits(_text(r.content))
    _render(r.content, "sparse", tmp_path)


def test_unknown_form_and_bad_signature():
    r = client.post("/form/fill", json={"session": SESSION, "form_id": "nope"})
    assert r.status_code == 400
    assert _post(SESSION, sig="not-base64!!").status_code == 400


def test_checkmarks_in_right_boxes(tmp_path):
    blank = _render((HERE / "sdge_care.pdf").read_bytes(), "blank", tmp_path)
    r = _post(SESSION)
    img = _render(r.content, "filled", tmp_path)
    for key in ("pa_calfresh", "pa_nslp", "inc_wages", "contact_email"):
        assert _ink(img, blank, key) > 3, key
    for key in ("pa_wic", "pa_ssi", "pa_medicaid", "inc_rent", "contact_mail"):
        assert _ink(img, blank, key) == 0, key
