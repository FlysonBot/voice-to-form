"""Overlay renderer and merger for flat government PDFs."""

from io import BytesIO

from pypdf import PdfReader, PdfWriter
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

FONT = "Helvetica"
MIN_SIZE = 6

try:  # FE-04 builds this module in parallel
    from form_engine.signature import draw_signature
except ImportError:  # pragma: no cover
    draw_signature = None


def _fit_text(text, font, size, max_width):
    """Shrink by 0.5 pt down to MIN_SIZE, then truncate. Returns (text, size)."""
    size = float(size)
    while size > MIN_SIZE and stringWidth(text, font, size) > max_width:
        size -= 0.5
    size = max(size, MIN_SIZE)
    while text and stringWidth(text, font, size) > max_width:
        text = text[:-1]
    return text, size


def _draw_comb(c, spec, value):
    """Draw only the digits of value, right-aligned, one per box. False if too many."""
    digits = "".join(ch for ch in value if ch.isdigit())
    xs = spec["comb"]["xs"]
    if not digits or len(digits) > len(xs):
        return False
    size = spec.get("font_size", 10)
    c.setFont(FONT, size)
    for ch, x in reversed(list(zip(digits[::-1], xs[::-1]))):  # draw left to right
        c.drawCentredString(x, spec["y"], ch)
    return True


def render_overlay(layout, values, signature_png=None):
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=tuple(layout["page_size"]))
    for key, spec in layout["fields"].items():
        value = values.get(key)
        kind = spec.get("kind")
        if kind == "text":
            # comb fields draw one digit per box; if the digits do not fit the
            # boxes, fall back to the old free-text drawing.
            if (
                isinstance(value, str)
                and value
                and not (spec.get("comb") and _draw_comb(c, spec, value))
            ):
                text, size = _fit_text(
                    value, FONT, spec.get("font_size", 10), spec.get("max_width", 1e9)
                )
                if text:
                    c.setFont(FONT, size)
                    c.drawString(spec["x"], spec["y"], text)
        elif kind == "checkbox":
            if value is True:
                x, y, s = spec["x"], spec["y"], spec["size"]
                c.setLineWidth(1.2)
                c.line(x + 0.2 * s, y + 0.5 * s, x + 0.42 * s, y + 0.2 * s)
                c.line(x + 0.42 * s, y + 0.2 * s, x + 0.82 * s, y + 0.82 * s)
        elif kind == "signature" and signature_png and draw_signature is not None:
            draw_signature(c, signature_png, spec)
    c.showPage()
    c.save()
    return buf.getvalue()


def merge_onto_form(blank_pdf_path, overlay_pdf):
    writer = PdfWriter()
    page = writer.add_page(PdfReader(blank_pdf_path).pages[0])
    page.merge_page(PdfReader(BytesIO(overlay_pdf)).pages[0])
    out = BytesIO()
    writer.write(out)
    return out.getvalue()
