import base64
import binascii
from io import BytesIO

from PIL import Image
from reportlab.lib.utils import ImageReader

MAX_BYTES = 5 * 1024 * 1024
MAX_SIDE = 4000
MAX_PIXELS = 4_000_000


def decode_signature(b64: str | None) -> bytes | None:
    if not b64:
        return None
    if b64.startswith("data:"):
        b64 = b64.split(",", 1)[-1]
    try:
        raw = base64.b64decode(b64, validate=False)
        if not raw or len(raw) > MAX_BYTES:
            raise ValueError
        img = Image.open(BytesIO(raw))
        w, h = img.size
        if max(w, h) > MAX_SIDE or w * h > MAX_PIXELS:
            raise ValueError
        img = img.convert("RGBA")
    except (ValueError, binascii.Error, OSError, Image.DecompressionBombError) as e:
        raise ValueError("invalid signature image") from e
    alpha = img.getchannel("A")
    if alpha.getextrema()[0] == 255:  # fully opaque: treat near-white as background
        px = img.load()
        for yy in range(img.height):
            for xx in range(img.width):
                r, g, b, _ = px[xx, yy]
                if r >= 240 and g >= 240 and b >= 240:
                    px[xx, yy] = (r, g, b, 0)
    bbox = img.getchannel("A").getbbox()
    if bbox is None:
        return None
    out = BytesIO()
    img.crop(bbox).save(out, format="PNG")
    return out.getvalue()


def draw_signature(c, png: bytes, box: dict) -> None:
    img = ImageReader(BytesIO(png))
    iw, ih = img.getSize()
    s = min(box["w"] / iw, box["h"] / ih)
    w, h = iw * s, ih * s
    x = box["x"] + (box["w"] - w) / 2
    y = box["y"] + (box["h"] - h) / 2
    c.drawImage(img, x, y, w, h, mask="auto")
