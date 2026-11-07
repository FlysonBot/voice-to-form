from io import BytesIO
from pathlib import Path

from pypdf import PdfReader
from reportlab.pdfbase.pdfmetrics import stringWidth

from form_engine import render

PDF = str(Path(__file__).resolve().parent.parent / "sdge_care.pdf")
LAYOUT = {
    "page_size": [612, 792],
    "fields": {
        "name": {"kind": "text", "x": 72, "y": 640, "font_size": 10, "max_width": 200},
        "email": {"kind": "text", "x": 72, "y": 620, "font_size": 10, "max_width": 100},
        "date": {"kind": "text", "x": 72, "y": 600, "font_size": 10, "max_width": 80},
        "pa_wic": {"kind": "checkbox", "x": 60, "y": 500, "size": 9},
        "pa_ssi": {"kind": "checkbox", "x": 60, "y": 480, "size": 9},
        "signature": {"kind": "signature", "x": 72, "y": 90, "w": 180, "h": 36},
    },
}
VALUES = {"name": "Maria Lopez", "email": "x" * 200, "pa_wic": True, "pa_ssi": False}


def test_overlay_valid():
    r = PdfReader(BytesIO(render.render_overlay(LAYOUT, VALUES)))
    assert len(r.pages) == 1
    assert [float(v) for v in r.pages[0].mediabox[2:]] == [612, 792]


def test_merge_text_and_pages(monkeypatch):
    calls = []
    monkeypatch.setattr(render, "draw_signature", lambda c, p, b: calls.append(b))
    ov = render.render_overlay(LAYOUT, VALUES, b"png")
    assert len(calls) == 1
    out = render.merge_onto_form(PDF, ov)
    r = PdfReader(BytesIO(out))
    assert len(r.pages) == 1
    assert [float(v) for v in r.pages[0].mediabox[2:]] == [612, 792]
    assert "Maria Lopez" in r.pages[0].extract_text()


def test_fit_text():
    text, size = render._fit_text("x" * 200, "Helvetica", 10, 100)
    assert size == 6
    assert stringWidth(text, "Helvetica", size) <= 100
    assert render._fit_text("hi", "Helvetica", 10, 100) == ("hi", 10.0)


COMB = {
    "kind": "text",
    "x": 224,
    "y": 140,
    "font_size": 10,
    "max_width": 50,
    "comb": {"xs": [20, 40, 60, 80, 100], "align": "right"},
}


class FakeCanvas:
    def __init__(self):
        self.centred, self.strings = [], []

    def setFont(self, *a):
        pass

    def drawCentredString(self, x, y, t):
        self.centred.append((x, y, t))

    def drawString(self, x, y, t):
        self.strings.append((x, y, t))


def test_comb_digits_right_aligned():
    c = FakeCanvas()
    assert render._draw_comb(c, COMB, "$38,400")
    assert sorted(c.centred) == [
        (20, 140, "3"),
        (40, 140, "8"),
        (60, 140, "4"),
        (80, 140, "0"),
        (100, 140, "0"),
    ]
    c = FakeCanvas()
    assert render._draw_comb(c, COMB, "1,440")  # 4 digits -> last four boxes
    assert [(x, t) for x, _, t in c.centred] == [
        (40, "1"),
        (60, "4"),
        (80, "4"),
        (100, "0"),
    ]


def test_comb_too_many_digits_falls_back():
    layout = {"page_size": [612, 792], "fields": {"annual_income": COMB}}
    c = FakeCanvas()
    assert not render._draw_comb(c, COMB, "111,440")
    out = render.render_overlay(layout, {"annual_income": "111,440"})
    assert len(PdfReader(BytesIO(out)).pages) == 1
    assert "111,440" in PdfReader(BytesIO(out)).pages[0].extract_text()


def test_comb_digits_in_overlay():
    layout = {"page_size": [612, 792], "fields": {"annual_income": COMB}}
    out = render.render_overlay(layout, {"annual_income": "38,400"})
    text = PdfReader(BytesIO(out)).pages[0].extract_text()
    assert "38,400" not in text
    assert "".join(text.split()) == "38400"


def test_non_comb_unchanged():
    layout = {"page_size": [612, 792], "fields": {"name": LAYOUT["fields"]["name"]}}
    out = render.render_overlay(layout, {"name": "Maria 38,400"})
    assert "Maria 38,400" in PdfReader(BytesIO(out)).pages[0].extract_text()
