import base64
from io import BytesIO

import pytest
from PIL import Image, ImageDraw
from reportlab.pdfgen import canvas

from form_engine.signature import decode_signature, draw_signature


def _png(blank=False):
    img = Image.new("RGBA", (200, 80), (0, 0, 0, 0))
    if not blank:
        ImageDraw.Draw(img).line((60, 40, 140, 40), fill=(0, 0, 0, 255), width=3)
    b = BytesIO()
    img.save(b, format="PNG")
    return b.getvalue()


def _b64(raw):
    return base64.b64encode(raw).decode()


def test_raw_and_trim():
    out = decode_signature(_b64(_png()))
    assert out and Image.open(BytesIO(out)).size[0] < 200


def test_data_url():
    assert decode_signature("data:image/png;base64," + _b64(_png()))


def test_none_empty():
    assert decode_signature(None) is None
    assert decode_signature("") is None


def test_garbage():
    with pytest.raises(ValueError):
        decode_signature(_b64(b"garbage"))
    with pytest.raises(ValueError):
        decode_signature("!!!notbase64")


def test_transparent():
    assert decode_signature(_b64(_png(blank=True))) is None


def test_draw():
    buf = BytesIO()
    c = canvas.Canvas(buf)
    draw_signature(
        c, decode_signature(_b64(_png())), {"x": 10, "y": 10, "w": 180, "h": 36}
    )
    c.save()
    assert buf.getvalue().startswith(b"%PDF") and len(buf.getvalue()) > 500


def _enc(img, fmt):
    b = BytesIO()
    img.save(b, format=fmt)
    return _b64(b.getvalue())


def test_pixel_limit():
    with pytest.raises(ValueError):
        decode_signature(_enc(Image.new("1", (5000, 5000)), "PNG"))


def test_white_jpeg_trimmed():
    img = Image.new("RGB", (200, 80), "white")
    ImageDraw.Draw(img).line((60, 40, 140, 40), fill=(0, 0, 0), width=4)
    out = decode_signature(_enc(img, "JPEG"))
    assert out and Image.open(BytesIO(out)).size[0] < 200


def test_opaque_white_png_trimmed():
    img = Image.new("RGBA", (200, 80), (255, 255, 255, 255))
    ImageDraw.Draw(img).line((60, 40, 140, 40), fill=(0, 0, 0, 255), width=3)
    out = decode_signature(_enc(img, "PNG"))
    w, h = Image.open(BytesIO(out)).size
    assert w < 200 and h < 80


def test_all_white():
    assert decode_signature(_enc(Image.new("RGB", (50, 50), "white"), "PNG")) is None
