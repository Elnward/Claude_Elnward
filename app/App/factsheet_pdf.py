"""v4.87.5: analysis fact sheet as a PDF - no third-party dependency.

The web UI's "Download > Fact sheet (PDF)" posts the run it is showing (the
same `DATA.run` shape webui_transform.to_frontend_run produces) plus the deck
and a few view choices (focus metric, the "What stands out" notes) to
web_server.py, which calls build_factsheet_pdf() and streams the bytes back.

A small hand-written PDF 1.4 writer is used on purpose: the app runs on the
user's own Python, and nothing beyond the standard library can be assumed
there. Text is set in DejaVu Sans Mono (App/fonts, embedded as TrueType with
WinAnsi encoding) so the sheet matches the monospace look of the web UI; all
charts are drawn as vector paths.
"""
from __future__ import annotations

import math
import zlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

FONT_DIR = Path(__file__).resolve().parent / "fonts"
ASSET_DIR = Path(__file__).resolve().parent / "factsheet_assets"
# v4.87.6: the neon sign in the top right of page 1 - the colour picture and
# its transparency mask as plain PNGs; their compressed pixel data is copied
# into the PDF unchanged (PNG and PDF share the same Flate + predictor format).
NEON_RGB, NEON_ALPHA = "neon_sign_rgb.png", "neon_sign_alpha.png"
FONT_FILES = {"R": "DejaVuSansMono.ttf", "B": "DejaVuSansMono-Bold.ttf"}
# Metrics read once from the font files (units per 1000 em): every glyph of a
# monospace font has the same advance, 1233/2048 em.
CHAR_W = 0.602
FONT_META = {
    "R": {"name": "DejaVuSansMono", "bbox": (-559, -375, 718, 1028)},
    "B": {"name": "DejaVuSansMono-Bold", "bbox": (-447, -394, 732, 1041)},
}
ASCENT, DESCENT, CAP_HEIGHT = 928, -236, 729

PAGE_W, PAGE_H = 595.28, 841.89  # A4 portrait, points
MARGIN = 42.0

# Web UI palette (webui/index.html :root), as 0..1 RGB.
def _hex(h: str) -> Tuple[float, float, float]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]


INK, INK2, INK3 = _hex("141412"), _hex("55554F"), _hex("8C8C84")
RULE, RULE2 = _hex("D5D5CD"), _hex("B9B9AF")
COBALT, COBALT_LIGHT, COBALT_PALE, COBALT_WASH = _hex("1557E8"), _hex("8FB0F4"), _hex("C7D7FA"), _hex("E4ECFC")
PAPER2 = _hex("EAEAE4")
WHITE = (1.0, 1.0, 1.0)

_REPLACE = {
    "≥": ">=", "≤": "<=", "→": "->", "←": "<-", "−": "-",
    " ": " ", " ": " ", " ": " ", "‑": "-", "‒": "-",
    "≈": "~", "×": "x", "✕": "x", "✓": "v",
}


def pdf_text(s: Any) -> bytes:
    """Unicode -> WinAnsi (cp1252) bytes, escaped for a PDF string literal."""
    s = "" if s is None else str(s)
    s = "".join(_REPLACE.get(ch, ch) for ch in s)
    raw = s.encode("cp1252", errors="replace")
    return raw.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def text_width(s: str, size: float, tracking: float = 0.0) -> float:
    n = len(str(s))
    return n * CHAR_W * size + max(0, n - 1) * tracking


def wrap(text: str, width: float, size: float) -> List[str]:
    per = max(1, int(width // (CHAR_W * size)))
    out: List[str] = []
    for para in str(text or "").split("\n"):
        words, line = para.split(" "), ""
        for w in words:
            while len(w) > per:  # hard-break very long tokens
                if line:
                    out.append(line)
                    line = ""
                out.append(w[:per])
                w = w[per:]
            cand = (line + " " + w) if line else w
            if len(cand) <= per:
                line = cand
            else:
                out.append(line)
                line = w
        out.append(line)
    return out


def fmt1(v: Any) -> str:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "-"
    r = round(f * 10) / 10
    return f"{r:,.1f}".rstrip("0").rstrip(".") if abs(r - round(r)) > 1e-9 else f"{int(round(r)):,}"


class Canvas:
    """Top-left based drawing API over PDF content streams (one per page)."""

    def __init__(self) -> None:
        self.pages: List[List[str]] = []
        self.target: Optional[int] = None  # draw into this page instead of the last one
        self.new_page()

    def new_page(self) -> None:
        self.pages.append([])

    @property
    def ops(self) -> List[str]:
        return self.pages[-1 if self.target is None else self.target]

    @staticmethod
    def _y(y: float) -> float:
        return PAGE_H - y

    @staticmethod
    def _c(rgb, stroke=False) -> str:
        return "%.3f %.3f %.3f %s" % (rgb[0], rgb[1], rgb[2], "RG" if stroke else "rg")

    def text(self, x: float, y: float, s: Any, size: float = 8.5, font: str = "R",
             color=INK, tracking: float = 0.0, align: str = "left") -> float:
        """y is the baseline. Returns the drawn width."""
        s = "" if s is None else str(s)
        w = text_width(s, size, tracking)
        if align == "right":
            x -= w
        elif align == "center":
            x -= w / 2
        self.ops.append("BT /F%s %.2f Tf %.2f Tc %s %.2f %.2f Td (%s) Tj ET" % (
            font, size, tracking, self._c(color), x, self._y(y), pdf_text(s).decode("latin-1")))
        return w

    def rect(self, x, y, w, h, fill=None, stroke=None, lw: float = 0.6) -> None:
        if w <= 0 or h <= 0:
            return
        parts = []
        if fill is not None:
            parts.append(self._c(fill))
        if stroke is not None:
            parts.append(self._c(stroke, True) + " %.2f w" % lw)
        op = "B" if fill is not None and stroke is not None else ("f" if fill is not None else "S")
        parts.append("%.2f %.2f %.2f %.2f re %s" % (x, self._y(y + h), w, h, op))
        self.ops.append("q " + " ".join(parts) + " Q")

    def line(self, x1, y1, x2, y2, color=INK, lw: float = 0.6, dash: Optional[str] = None) -> None:
        d = ("[%s] 0 d " % dash) if dash else ""
        self.ops.append("q %s%s %.2f w %.2f %.2f m %.2f %.2f l S Q" % (
            d, self._c(color, True), lw, x1, self._y(y1), x2, self._y(y2)))

    def poly(self, pts: Sequence[Tuple[float, float]], stroke=None, fill=None, lw: float = 1.0,
             close: bool = False, alpha_gs: Optional[str] = None) -> None:
        if len(pts) < 2:
            return
        path = "%.2f %.2f m " % (pts[0][0], self._y(pts[0][1])) + " ".join(
            "%.2f %.2f l" % (x, self._y(y)) for x, y in pts[1:])
        if close:
            path += " h"
        parts = ["q"]
        if alpha_gs:
            parts.append("/%s gs" % alpha_gs)
        if fill is not None:
            parts.append(self._c(fill))
        if stroke is not None:
            parts.append(self._c(stroke, True) + " %.2f w 1 J 1 j" % lw)
        op = "B" if fill is not None and stroke is not None else ("f" if fill is not None else "S")
        parts.append(path + " " + op + " Q")
        self.ops.append(" ".join(parts))

    def image(self, name: str, x: float, y: float, w: float, h: float) -> None:
        """Draw an image XObject registered in render_pdf (top-left based box)."""
        self.ops.append("q %.2f 0 0 %.2f %.2f %.2f cm /%s Do Q" % (w, h, x, self._y(y + h), name))

    def circle(self, cx, cy, r, fill=COBALT) -> None:
        k = 0.5523 * r
        y = self._y(cy)
        self.ops.append("q %s %.2f %.2f m %.2f %.2f %.2f %.2f %.2f %.2f c %.2f %.2f %.2f %.2f %.2f %.2f c "
                        "%.2f %.2f %.2f %.2f %.2f %.2f c %.2f %.2f %.2f %.2f %.2f %.2f c f Q" % (
                            self._c(fill), cx + r, y,
                            cx + r, y + k, cx + k, y + r, cx, y + r,
                            cx - k, y + r, cx - r, y + k, cx - r, y,
                            cx - r, y - k, cx - k, y - r, cx, y - r,
                            cx + k, y - r, cx + r, y - k, cx + r, y))


def _font_objects(objs: "PdfObjects", key: str) -> int:
    data = (FONT_DIR / FONT_FILES[key]).read_bytes()
    comp = zlib.compress(data, 9)
    ff = objs.add(b"<< /Length %d /Length1 %d /Filter /FlateDecode >>\nstream\n" % (len(comp), len(data)) + comp + b"\nendstream")
    meta = FONT_META[key]
    bb = meta["bbox"]
    desc = objs.add((
        "<< /Type /FontDescriptor /FontName /%s /Flags 33 /FontBBox [%d %d %d %d] /ItalicAngle 0 "
        "/Ascent %d /Descent %d /CapHeight %d /StemV %d /FontFile2 %d 0 R >>" % (
            meta["name"], bb[0], bb[1], bb[2], bb[3], ASCENT, DESCENT, CAP_HEIGHT,
            120 if key == "B" else 80, ff)).encode())
    widths = " ".join(["602"] * (255 - 32 + 1))
    return objs.add((
        "<< /Type /Font /Subtype /TrueType /BaseFont /%s /FirstChar 32 /LastChar 255 /Widths [%s] "
        "/Encoding /WinAnsiEncoding /FontDescriptor %d 0 R >>" % (meta["name"], widths, desc)).encode())


class PdfObjects:
    def __init__(self) -> None:
        self.items: List[Optional[bytes]] = []

    def reserve(self) -> int:
        self.items.append(None)
        return len(self.items)

    def add(self, body: bytes) -> int:
        self.items.append(body)
        return len(self.items)

    def set(self, num: int, body: bytes) -> None:
        self.items[num - 1] = body

    def render(self, root: int, info: int) -> bytes:
        out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = []
        for i, body in enumerate(self.items, start=1):
            offsets.append(len(out))
            out += b"%d 0 obj\n" % i + (body or b"null") + b"\nendobj\n"
        xref = len(out)
        out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(self.items) + 1)
        for off in offsets:
            out += b"%010d 00000 n \n" % off
        out += b"trailer\n<< /Size %d /Root %d 0 R /Info %d 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
            len(self.items) + 1, root, info, xref)
        return bytes(out)


def read_png(path: Path) -> Tuple[int, int, int, bytes]:
    """(width, height, colour type, concatenated IDAT bytes) of a simple
    8-bit, non-interlaced PNG - enough to embed it without decoding."""
    import struct
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG: %s" % path.name)
    pos, idat = 8, bytearray()
    w = h = 0
    ctype = -1
    while pos < len(data):
        n = struct.unpack(">I", data[pos:pos + 4])[0]
        kind = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + n]
        if kind == b"IHDR":
            w, h, depth, ctype, _c, _f, interlace = struct.unpack(">IIBBBBB", body)
            if depth != 8 or interlace != 0 or ctype not in (0, 2):
                raise ValueError("unsupported PNG layout: %s" % path.name)
        elif kind == b"IDAT":
            idat += body
        elif kind == b"IEND":
            break
        pos += 12 + n
    return w, h, ctype, bytes(idat)


def _neon_objects(objs: "PdfObjects") -> Optional[int]:
    try:
        w, h, ct, rgb = read_png(ASSET_DIR / NEON_RGB)
        aw, ah, act, alpha = read_png(ASSET_DIR / NEON_ALPHA)
    except (OSError, ValueError):
        return None  # the sheet still builds without the sign
    if ct != 2 or act != 0 or (w, h) != (aw, ah):
        return None
    mask = objs.add(b"<< /Type /XObject /Subtype /Image /Width %d /Height %d /ColorSpace /DeviceGray /BitsPerComponent 8 "
                    b"/Filter /FlateDecode /DecodeParms << /Predictor 15 /Colors 1 /BitsPerComponent 8 /Columns %d >> "
                    b"/Length %d >>\nstream\n" % (w, h, w, len(alpha)) + alpha + b"\nendstream")
    return objs.add(b"<< /Type /XObject /Subtype /Image /Width %d /Height %d /ColorSpace /DeviceRGB /BitsPerComponent 8 "
                    b"/Filter /FlateDecode /DecodeParms << /Predictor 15 /Colors 3 /BitsPerComponent 8 /Columns %d >> "
                    b"/SMask %d 0 R /Length %d >>\nstream\n" % (w, h, w, mask, len(rgb)) + rgb + b"\nendstream")


def neon_size() -> Optional[Tuple[int, int]]:
    try:
        w, h, _ct, _d = read_png(ASSET_DIR / NEON_RGB)
        return w, h
    except (OSError, ValueError):
        return None


def render_pdf(canvas: Canvas, title: str) -> bytes:
    objs = PdfObjects()
    pages_id = objs.reserve()
    f_r = _font_objects(objs, "R")
    f_b = _font_objects(objs, "B")
    gs = objs.add(b"<< /Type /ExtGState /ca 0.14 /CA 0.14 >>")
    neon = _neon_objects(objs) if any("/Neon Do" in op for page in canvas.pages for op in page) else None
    xobj = (" /XObject << /Neon %d 0 R >>" % neon) if neon else ""
    if not neon:  # never reference an image that is not there
        for page in canvas.pages:
            page[:] = [op for op in page if "/Neon Do" not in op]
    res = "<< /Font << /FR %d 0 R /FB %d 0 R >> /ExtGState << /GSband %d 0 R >>%s >>" % (f_r, f_b, gs, xobj)
    kids = []
    for ops in canvas.pages:
        stream = zlib.compress("\n".join(ops).encode("latin-1"), 9)
        c = objs.add(b"<< /Length %d /Filter /FlateDecode >>\nstream\n" % len(stream) + stream + b"\nendstream")
        kids.append(objs.add(("<< /Type /Page /Parent %d 0 R /MediaBox [0 0 %.2f %.2f] /Resources %s /Contents %d 0 R >>" % (
            pages_id, PAGE_W, PAGE_H, res, c)).encode()))
    objs.set(pages_id, ("<< /Type /Pages /Kids [%s] /Count %d >>" % (" ".join("%d 0 R" % k for k in kids), len(kids))).encode())
    root = objs.add(("<< /Type /Catalog /Pages %d 0 R >>" % pages_id).encode())
    info = objs.add(b"<< /Title (" + pdf_text(title) + b") /Producer (Urza's Spearfishing Guide) /CreationDate (D:" +
                    datetime.now().strftime("%Y%m%d%H%M%S").encode() + b") >>")
    return objs.render(root, info)


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

class Sheet:
    """Flowing layout on top of Canvas: a y-cursor, page breaks, footer."""
    BOTTOM = PAGE_H - MARGIN - 18

    def __init__(self, deck_name: str, stamp: str) -> None:
        self.c = Canvas()
        self.deck_name = deck_name
        self.stamp = stamp
        self.y = MARGIN
        self.width = PAGE_W - 2 * MARGIN
        self._page_head()

    def _page_head(self) -> None:
        c = self.c
        c.text(MARGIN, MARGIN + 6, "URZA'S SPEARFISHING GUIDE", 6.5, "B", INK, tracking=1.1)
        c.text(PAGE_W - MARGIN, MARGIN + 6, "Fact sheet, " + self.stamp, 6.5, "R", INK3, align="right")
        self.y = MARGIN + 22

    def need(self, h: float) -> None:
        if self.y + h > self.BOTTOM:
            self.c.new_page()
            self._page_head()
            self.y += 6

    def section(self, title: str, sub: str = "") -> None:
        self.need(44)
        self.y += 10
        self.c.line(MARGIN, self.y, PAGE_W - MARGIN, self.y, INK, 0.8)
        self.y += 15
        self.c.text(MARGIN, self.y, title.upper(), 7.2, "B", INK, tracking=1.0)
        if sub:
            self.y += 11
            for ln in wrap(sub, self.width, 7.2):
                self.c.text(MARGIN, self.y, ln, 7.2, "R", INK3)
                self.y += 9.5
            self.y -= 9.5
        self.y += 14

    def para(self, text: str, size: float = 8.2, color=INK2, width: Optional[float] = None,
             x: float = MARGIN, lead: float = 1.45, font: str = "R") -> None:
        for ln in wrap(text, width or self.width, size):
            self.need(size * lead)
            self.c.text(x, self.y + size * 0.78, ln, size, font, color)
            self.y += size * lead

    def finish(self, title: str) -> bytes:
        n = len(self.c.pages)
        y = PAGE_H - MARGIN + 4
        for i in range(n):
            self.c.target = i
            self.c.line(MARGIN, y - 12, PAGE_W - MARGIN, y - 12, RULE, 0.5)
            self.c.text(MARGIN, y, "Goldfish results are a deck-building heuristic, not pod win rates.", 6.5, "R", INK3)
            self.c.text(PAGE_W - MARGIN, y, "%s  |  page %d of %d" % (self.deck_name[:40], i + 1, n), 6.5, "R", INK3, align="right")
        self.c.target = None
        return render_pdf(self.c, title)


# ---------------------------------------------------------------------------
# Building blocks
# ---------------------------------------------------------------------------

def _kv_block(s: Sheet, rows: List[Tuple[str, str]], x: float, width: float, key_w: float = 118) -> float:
    """Label/value rows; returns the height used (does not move s.y)."""
    y0 = s.y
    y = y0
    for k, v in rows:
        lines = wrap(v, width - key_w, 8.0) or [""]
        s.c.text(x, y + 7, k, 7.0, "R", INK3)
        for ln in lines:
            s.c.text(x + key_w, y + 7, ln, 8.0, "R", INK)
            y += 11.2
        y += 3
        s.c.line(x, y - 1.5, x + width, y - 1.5, RULE, 0.4)
        y += 2
    return y - y0


def _facts(s: Sheet, facts: List[Tuple[str, str, str]]) -> None:
    """A row of key figures: (label, value, unit)."""
    s.need(44)
    s.c.line(MARGIN, s.y, PAGE_W - MARGIN, s.y, INK, 0.8)
    x = MARGIN
    cell = s.width / max(1, len(facts))
    for i, (k, v, u) in enumerate(facts):
        s.c.text(x + (0 if i == 0 else 9), s.y + 12, k.upper(), 5.6, "R", INK3, tracking=0.6)
        w = s.c.text(x + (0 if i == 0 else 9), s.y + 31, v, 15, "R", INK)
        if u:
            s.c.text(x + (0 if i == 0 else 9) + w + 3, s.y + 31, u, 7.5, "R", INK3)
        if i:
            s.c.line(x, s.y + 3, x, s.y + 38, RULE, 0.5)
        x += cell
    s.y += 42
    s.c.line(MARGIN, s.y, PAGE_W - MARGIN, s.y, RULE, 0.5)
    s.y += 8


def _hbar(s: Sheet, x, y, w, frac, h=4.0, color=COBALT, track=COBALT_WASH) -> None:
    s.c.rect(x, y, w, h, fill=track)
    if frac > 0:
        s.c.rect(x, y, max(0.8, w * min(1.0, frac)), h, fill=color)


def _stack_rows(s: Sheet, rows: List[Tuple[str, List[float]]], series: List[Tuple[str, Any, Any]]) -> None:
    """Stacked 100 % bars (outcome by opponent)."""
    lx = MARGIN
    for name, col, _txt in series:
        s.c.rect(lx, s.y, 6, 6, fill=col)
        lx += 10 + s.c.text(lx + 10, s.y + 5.6, name, 6.6, "R", INK2) + 12
    s.y += 16
    label_w = 70
    bw = s.width - label_w
    for label, parts in rows:
        s.need(20)
        s.c.text(MARGIN, s.y + 9, label, 8.0, "R", INK)
        x = MARGIN + label_w
        for (name, col, txtc), v in zip(series, parts):
            v = max(0.0, float(v or 0))
            w = bw * v / 100.0
            if w <= 0.3:
                continue
            s.c.rect(x, s.y, max(0.8, w - 1.2), 13, fill=col)
            lab = fmt1(v) + "%"
            if w > text_width(lab, 6.5) + 8:
                s.c.text(x + 4, s.y + 9, lab, 6.5, "R", txtc)
            x += w
        s.y += 19


def _line_chart(s: Sheet, pts: List[dict], x, y, w, h, unit: str, ref: Optional[float] = None,
                band: bool = True) -> None:
    """pts: [{t, avg, p25?, p75?}]"""
    if not pts:
        return
    vals = [float(p.get("avg") or 0) for p in pts]
    his = [float(p["p75"]) for p in pts if band and p.get("p75") is not None]
    tops = [float(p["top"]) for p in pts if band and p.get("top") is not None]
    top = max(vals + his + tops + ([ref] if ref else []) + [1.0])
    ymax = _nice(top * 1.08)
    ml, mb = 26, 14
    cw, chh = w - ml - 30, h - mb - 6
    t0, t1 = pts[0]["t"], pts[-1]["t"]
    X = lambda t: x + ml + (cw * (t - t0) / (t1 - t0) if t1 != t0 else cw / 2)  # noqa: E731
    Y = lambda v: y + 6 + chh * (1 - float(v) / ymax)  # noqa: E731
    for i in range(5):
        v = ymax * i / 4
        yy = Y(v)
        s.c.line(x + ml, yy, x + ml + cw, yy, INK if i == 0 else RULE, 0.6 if i == 0 else 0.4)
        s.c.text(x + ml - 5, yy + 2.3, fmt1(v), 6.0, "R", INK3, align="right")
    step = max(1, math.ceil(len(pts) / 12))
    for i, p in enumerate(pts):
        if i % step == 0 or i == len(pts) - 1:
            s.c.text(X(p["t"]), y + h - 2, "T%d" % p["t"], 6.0, "R", INK3, align="center")
    if ref is not None:
        s.c.line(x + ml, Y(ref), x + ml + cw, Y(ref), INK2, 0.6, dash="2 2")
        s.c.text(x + ml + cw, Y(ref) - 3, "start %s" % fmt1(ref), 6.0, "R", INK2, align="right")
    if band and all(p.get("p25") is not None and p.get("p75") is not None for p in pts):
        up = [(X(p["t"]), Y(p["p75"])) for p in pts]
        dn = [(X(p["t"]), Y(p["p25"])) for p in reversed(pts)]
        s.c.poly(up + dn, fill=COBALT, close=True, alpha_gs="GSband")
    if band and all(p.get("top") is not None for p in pts):
        tl = [(X(p["t"]), Y(p["top"])) for p in pts]
        for (x1, y1), (x2, y2) in zip(tl, tl[1:]):
            s.c.line(x1, y1, x2, y2, COBALT_LIGHT, 0.8, dash="2 1.5")
    line = [(X(p["t"]), Y(p.get("avg") or 0)) for p in pts]
    s.c.poly(line, stroke=COBALT, lw=1.4)
    lx, ly = line[-1]
    s.c.circle(lx, ly, 2.4)
    s.c.text(lx + 5, ly + 2.5, fmt1(vals[-1]), 6.8, "R", INK)


def _columns(s: Sheet, data: List[Tuple[str, float]], x, y, w, h) -> None:
    if not data:
        return
    ymax = _nice(max([v for _, v in data] + [1]))
    ml, mb = 22, 14
    cw, chh = w - ml, h - mb - 6
    band = cw / len(data)
    bw = min(14, band * 0.6)
    for i in range(5):
        v = ymax * i / 4
        yy = y + 6 + chh * (1 - v / ymax)
        s.c.line(x + ml, yy, x + ml + cw, yy, INK if i == 0 else RULE, 0.6 if i == 0 else 0.4)
        s.c.text(x + ml - 4, yy + 2.3, fmt1(v), 6.0, "R", INK3, align="right")
    base = y + 6 + chh
    for i, (k, v) in enumerate(data):
        cx = x + ml + band * i + band / 2
        hh = chh * max(0.0, v) / ymax
        s.c.rect(cx - bw / 2, base - hh, bw, hh, fill=COBALT)
        if i in (0, len(data) - 1):
            s.c.text(cx, base - hh - 3, fmt1(v), 6.0, "R", INK, align="center")
        s.c.text(cx, y + h - 2, k, 6.0, "R", INK3, align="center")


def _nice(v: float) -> float:
    if v <= 0:
        return 1.0
    p = 10 ** math.floor(math.log10(v))
    n = v / p
    return (1 if n <= 1 else 2 if n <= 2 else 2.5 if n <= 2.5 else 5 if n <= 5 else 10) * p


_TYPE_ORDER = [("Creature", "Creatures"), ("Planeswalker", "Planeswalkers"), ("Battle", "Battles"),
               ("Instant", "Instants"), ("Sorcery", "Sorceries"), ("Artifact", "Artifacts"),
               ("Enchantment", "Enchantments"), ("Land", "Lands")]


def _deck_groups(cards: List[dict]) -> List[Tuple[str, List[dict]]]:
    groups: Dict[str, List[dict]] = {}
    for c in cards:
        if c.get("cmd"):
            groups.setdefault("Commander", []).append(c)
            continue
        t = str(c.get("t") or "")
        label = "Other"
        for key, lab in _TYPE_ORDER:
            if key == "Land" and "Land" in t:
                label = lab
                break
            if key in t and "Land" not in t:
                label = lab
                break
        groups.setdefault(label, []).append(c)
    order = ["Commander"] + [lab for _, lab in _TYPE_ORDER] + ["Other"]
    return [(lab, sorted(groups[lab], key=lambda c: (float(c.get("mv") or 0), c.get("n", "")))) for lab in order if lab in groups]


# ---------------------------------------------------------------------------
# The fact sheet
# ---------------------------------------------------------------------------

def build_factsheet_pdf(payload: Dict[str, Any]) -> bytes:
    run = payload.get("run") or {}
    deck = payload.get("deck") or {}
    view = payload.get("view") or {}
    table = payload.get("table") or {}
    sim = run.get("simulation") or {}
    o = run.get("outcomes") or {}
    name = str(deck.get("name") or "Deck")
    stamp = str(view.get("generated") or datetime.now().strftime("%d.%m.%Y, %H:%M"))
    s = Sheet(name, stamp)
    c = s.c

    # --- title -------------------------------------------------------------
    sign = neon_size()
    title_w = s.width - (140 if sign else 0)
    if sign:  # the neon sign sits top right, under the "Fact sheet, <date>" line
        sh = 64.0
        sw = sh * sign[0] / sign[1]
        c.image("Neon", PAGE_W - MARGIN - sw, MARGIN + 13, sw, sh)
    tsize = 22.0 if text_width(name, 22) <= title_w else max(13.0, title_w / (len(name) * CHAR_W))
    title = name if text_width(name, tsize) <= title_w else name[: int(title_w // (CHAR_W * tsize)) - 1] + "."
    c.text(MARGIN, s.y + 20, title, tsize, "B", INK)
    s.y += 30
    cmdrs = " & ".join(deck.get("commanders") or []) or "No commander selected"
    c.text(MARGIN, s.y + 9, cmdrs, 9, "R", INK2)
    s.y += 14
    c.text(MARGIN, s.y + 8, str(run.get("run_label") or "Latest run"), 7.2, "R", INK3)
    s.y += 16

    # --- setup ---------------------------------------------------------------
    s.section("Setup", "What this run was simulated with")
    ps = deck.get("playstyle") or {}
    tags = deck.get("tags") or sim.get("strategy_tags") or []
    left = [
        ("Commander", cmdrs),
        ("Strategy tags", ", ".join(view.get("tag_labels") or tags) or "none set"),
        ("Play style", "aggression %s, attacker selection %s, block willingness %s" % (
            fmt1(ps.get("aggression", 100)), fmt1(ps.get("attacker_selection", 100)), fmt1(ps.get("block_willingness", 50)))),
        ("Win conditions", ", ".join(x.get("name", "") for x in (run.get("scen") or [])) or "none configured"),
    ]
    tp = "off"
    if table:
        if table.get("enabled", True):
            tp = "on, %s targeting; kingmaking below %s life, revenge weight %s" % (
                "threat (attack the leader)" if table.get("target_mode") == "threat" else "uniform",
                fmt1(table.get("kingmaking_life_threshold")), fmt1(table.get("kingmaking_revenge_weight")))
    right = [
        ("Games / turns", "%s games of %s turns, seed %s" % (sim.get("runs", "-"), sim.get("turns", "-"), sim.get("seed", "-"))),
        ("Opponents", str(view.get("opponents") or sim.get("opponent_profile") or "-")),
        ("Opponent model", "three Bracket-3 seats (advanced)" if sim.get("advanced_opponent_model") else "one abstract pressure profile"),
        ("Commander posture", str(view.get("posture") or sim.get("commander_posture") or "auto")),
        ("Table politics", tp if table else "not recorded"),
        ("Engine", str(sim.get("engine_version") or "-")),
    ]
    col = (s.width - 24) / 2
    h1 = _kv_block(s, left, MARGIN, col, key_w=92)
    h2 = _kv_block(s, right, MARGIN + col + 24, col, key_w=96)
    s.y += max(h1, h2) + 6

    # --- headline -------------------------------------------------------------
    s.section("Results")
    scen = run.get("scen") or []
    reach = o.get("win_condition_reach_pct")
    if reach is None and scen:
        reach = max(float(x.get("reach") or 0) for x in scen)
    s.need(62)
    if scen:
        top = s.y
        w = c.text(MARGIN, top + 40, fmt1(reach or 0), 44, "B", COBALT)
        w += 4 + c.text(MARGIN + w + 4, top + 40, "%", 18, "B", COBALT)
        s.y = top + 12
        best = max(scen, key=lambda z: float(z.get("reach") or 0))
        s.para("of %s games reached %s within %s turns. Strongest on its own: %s at %s %%." % (
            sim.get("runs", "-"), "one of the %d configured win-condition setups" % len(scen) if len(scen) > 1
            else "the configured win-condition setup", sim.get("turns", "-"), best.get("name", ""), fmt1(best.get("reach") or 0)),
            size=8.4, color=INK, width=s.width * 0.62, x=MARGIN + w + 18)
        s.y = max(s.y, top + 52) + 4
    else:
        s.para("No win-condition setups were part of this run; the figures below describe games won and lost outright.", color=INK)
        s.y += 6
    win, loss = float(o.get("win_by_turn_limit_pct") or 0), float(o.get("loss_by_turn_limit_pct") or 0)
    _facts(s, [
        ("Win", fmt1(win), "%"), ("Loss", fmt1(loss), "%"),
        ("Open at turn %s" % sim.get("turns", "-"), fmt1(max(0.0, 100 - win - loss)), "%"),
        ("Median win turn", fmt1(o.get("median_win_turn_when_winning")) if o.get("median_win_turn_when_winning") is not None else "-", ""),
        ("Cards drawn", fmt1(o.get("avg_cards_drawn")), ""),
        ("Mulligans", "%.2f" % float((run.get("opening") or {}).get("avg_mulligans") or 0), ""),
        ("Opponents out", fmt1(o.get("avg_opponents_eliminated") or 0), "/ 3"),
    ])

    opp = run.get("opp") or {}
    order = [k for k in ("aggro", "midrange", "control", "horde") if k in opp]
    if order:
        s.section("Outcome by opponent profile", "%d games each" % round(float(sim.get("runs") or 0) / len(order)))
        _stack_rows(s, [(k.capitalize(), [opp[k].get("win_pct"), opp[k].get("loss_pct"), opp[k].get("active_at_limit_pct")]) for k in order],
                    [("Win", COBALT, WHITE), ("Loss", INK, WHITE), ("Open at turn %s" % sim.get("turns", "-"), RULE2, INK)])

    # --- win conditions -------------------------------------------------------
    if scen:
        s.section("Win conditions", "Share of games in which each setup came together; not proof the combo resolves through interaction")
        for x in sorted(scen, key=lambda z: -float(z.get("reach") or 0)):
            s.need(40)
            c.text(MARGIN, s.y + 8, x.get("name", ""), 8.4, "B", INK)
            meta = []
            if x.get("median_turn") is not None:
                meta.append("usually by turn %s" % fmt1(x["median_turn"]))
            if x.get("target_scope") in ("any", "mixed"):
                meta.append("single target")
            if meta:
                c.text(MARGIN, s.y + 19, ", ".join(meta), 6.8, "R", INK3)
            bx = MARGIN + s.width * 0.52
            bw = s.width * 0.36
            c.text(bx, s.y + 7, "Setup reached", 6.8, "R", INK2)
            _hbar(s, bx + 88, s.y + 3, bw - 88, float(x.get("reach") or 0) / 100, h=4.5)
            c.text(PAGE_W - MARGIN, s.y + 7.5, fmt1(x.get("reach") or 0) + " %", 7.4, "B", INK, align="right")
            c.text(bx, s.y + 19, "Cards and thresholds", 6.8, "R", INK2)
            _hbar(s, bx + 88, s.y + 16, bw - 88, float(x.get("cards") or 0) / 100, h=2.5, color=INK3, track=PAPER2)
            c.text(PAGE_W - MARGIN, s.y + 19.5, fmt1(x.get("cards") or 0) + " %", 7.0, "R", INK2, align="right")
            s.y += 26
            bn = (x.get("bn") or [])[:3]
            if bn:
                runs = float(sim.get("runs") or 1)
                txt = "Most often missing: " + "; ".join("%s (%s of %d)" % (str(b[0]).replace(" x1 in ", " in "), b[1], runs) for b in bn)
                s.para(txt, size=6.8, color=INK3, width=s.width)
            s.c.line(MARGIN, s.y + 2, PAGE_W - MARGIN, s.y + 2, RULE, 0.4)
            s.y += 8

    # --- focus metric ----------------------------------------------------------
    focus = view.get("focus") or {}
    fm = (run.get("metrics") or {}).get(focus.get("key") or "")
    if fm and fm.get("by_turn"):
        s.section("Focus: " + str(fm.get("label", "")),
                  "Left: share of games that reached each value at least once, in any turn. Right: per turn - "
                  "average (line), middle half of the games still running (band), best 10 % (dashed).")
        s.need(170)
        top = s.y
        bench = focus.get("benchmarks") or []
        bw = s.width * 0.38
        yy = top
        for b in bench[:8]:
            c.text(MARGIN, yy + 7, str(b.get("label", "")), 7.6, "R", COBALT if b.get("mine") else INK)
            c.text(MARGIN + bw, yy + 7, fmt1(b.get("p") or 0) + " %", 7.6, "R", INK, align="right")
            _hbar(s, MARGIN, yy + 10, bw, float(b.get("p") or 0) / 100, h=2.6)
            yy += 19
        base = 40.0 if focus.get("key") in ("life", "opp_life_min") else None
        pts = [dict(p, top=p.get("p10" if fm.get("dir") == "down" else "p90")) for p in fm["by_turn"]]
        _line_chart(s, pts, MARGIN + bw + 26, top - 4, s.width - bw - 26, 158, fm.get("unit", ""), ref=base)
        s.y = max(yy, top + 158) + 6
        if focus.get("summary"):
            s.para(focus["summary"], size=7.4, color=INK2)

    bt = run.get("byturn") or []
    if bt:
        s.section("Mana at start of main phase", "Average available mana per turn")
        s.need(120)
        _columns(s, [("T%d" % d["t"], float(d.get("avg_mana_start_main") or 0)) for d in bt], MARGIN, s.y, s.width, 110)
        s.y += 118

    # --- notes ------------------------------------------------------------------
    tips = view.get("tips") or []
    if tips:
        s.section("What stands out", "Checks against the reference decks and this run's outcomes")
        for kind in ("pro", "con"):
            items = [t for t in tips if t.get("kind") == kind]
            if not items:
                continue
            s.need(20)
            c.text(MARGIN, s.y + 7, "STRENGTHS" if kind == "pro" else "WATCH OUT FOR", 6.4, "B", INK3, tracking=0.8)
            s.y += 14
            for t in items:
                lines = wrap(str(t.get("body", "")), s.width - 16, 7.6)
                s.need(16 + 10.5 * len(lines))
                h = 14 + 10.5 * len(lines) + 6
                c.rect(MARGIN, s.y, s.width, h, fill=COBALT_WASH if kind == "pro" else PAPER2)
                c.text(MARGIN + 8, s.y + 11, str(t.get("title", "")), 7.8, "B", INK)
                yy = s.y + 23
                for ln in lines:
                    c.text(MARGIN + 8, yy, ln, 7.6, "R", INK2)
                    yy += 10.5
                s.y += h + 5
            s.y += 4

    gaps = run.get("model_gaps") or []
    if gaps:
        s.section("Simulation coverage", "%d key card(s) are not (fully) simulated; read the win rate as a lower bound" % int(run.get("model_gaps_total") or len(gaps)))
        why = {"never_cast": "never cast", "no_modeled_effect": "ability not simulated"}
        for g in gaps:
            s.para("%s  (%s)%s" % (g.get("name", ""), why.get(g.get("reason"), g.get("reason", "")),
                                   (": " + g["detail"]) if g.get("detail") else ""), size=7.4, color=INK2)

    # --- card highlights ------------------------------------------------------------
    hl = run.get("hl") or []
    if hl:
        s.section("Card highlights", "Modeled value per time a card was seen, in mana equivalents")
        vmax = max(float(h.get("value_per_seen") or 0) for h in hl) or 1
        for h in hl:
            s.need(15)
            tier = str(h.get("tier", ""))
            c.rect(MARGIN, s.y + 1, 10, 10, fill=INK if tier == "S" else None, stroke=INK, lw=0.6)
            c.text(MARGIN + 5, s.y + 8.8, tier, 6.6, "B", WHITE if tier == "S" else INK, align="center")
            c.text(MARGIN + 18, s.y + 9, h.get("name", ""), 7.8, "R", INK)
            _hbar(s, MARGIN + s.width * 0.5, s.y + 5, s.width * 0.34, float(h.get("value_per_seen") or 0) / vmax, h=3)
            c.text(PAGE_W - MARGIN, s.y + 9, "%.2f" % float(h.get("value_per_seen") or 0), 7.6, "R", INK, align="right")
            s.y += 15

    # --- reference ---------------------------------------------------------------------
    ar = run.get("archetype_reference") or {}
    io = ar.get("identity_only") or {}
    comp = io.get("comparison") or []
    if comp:
        labels = {"n_lands": "Lands", "n_ramp": "Ramp", "n_card_advantage": "Card advantage",
                  "n_interaction_total": "Interaction, total", "n_boardwipes": "- board wipes",
                  "n_protection": "Protection", "n_strategy_cards": "Strategy cards", "n_creatures": "Creatures",
                  "avg_nonland_cmc": "Avg. mana value (nonland)"}
        s.section("Reference: EDHREC decks", "%s color identity, this deck against the average deck" % (ar.get("identity_label") or ""))
        cols = [MARGIN, MARGIN + s.width * 0.42, MARGIN + s.width * 0.62, PAGE_W - MARGIN]
        s.need(20)
        for i, head in enumerate(["CATEGORY", "THIS DECK", "REFERENCE", "DIFFERENCE"]):
            c.text(cols[i] if i == 0 else cols[i] + (0 if i < 3 else 0), s.y + 7, head, 6.0, "R", INK3,
                   tracking=0.6, align="left" if i == 0 else "right")
        s.y += 11
        c.line(MARGIN, s.y, PAGE_W - MARGIN, s.y, INK, 0.7)
        s.y += 4
        for r in comp:
            s.need(14)
            diff = float(r.get("diff") or 0)
            pct = r.get("diff_pct")
            c.text(MARGIN, s.y + 8, labels.get(r.get("field"), r.get("field", "")), 7.6, "R", INK)
            c.text(cols[1], s.y + 8, fmt1(r.get("observed")), 7.6, "R", INK, align="right")
            c.text(cols[2], s.y + 8, fmt1(r.get("expected")), 7.6, "R", INK, align="right")
            c.text(cols[3], s.y + 8, ("+" if diff >= 0 else "") + fmt1(diff) + ("" if pct is None else " (%s%s %%)" % ("+" if pct >= 0 else "", fmt1(pct))),
                   7.6, "R", INK, align="right")
            s.y += 12
            c.line(MARGIN, s.y, PAGE_W - MARGIN, s.y, RULE, 0.4)
            s.y += 2

    # --- deck list ------------------------------------------------------------------------
    cards = deck.get("cards") or []
    if cards:
        total = sum(int(x.get("q") or 1) for x in cards)
        s.c.new_page()
        s._page_head()
        s.section("Deck list", "%d cards" % total)
        groups = _deck_groups(cards)
        ncol = 3
        gap = 16
        colw = (s.width - gap * (ncol - 1)) / ncol
        line_h = 10.2
        # balance columns by line count
        blocks = [(lab, items) for lab, items in groups]
        heights = [16 + len(items) * line_h + 8 for _, items in blocks]
        target = sum(heights) / ncol
        colx, coly, ci, used = MARGIN, s.y, 0, 0.0
        top = s.y
        max_char = int(colw // (CHAR_W * 7.2))
        for (lab, items), hgt in zip(blocks, heights):
            if ci < ncol - 1 and used > 0 and used + hgt / 2 > target:
                ci += 1
                used = 0.0
                colx = MARGIN + ci * (colw + gap)
                coly = top
            if coly + hgt > s.BOTTOM:
                if ci < ncol - 1:
                    ci += 1
                    colx = MARGIN + ci * (colw + gap)
                    coly = top
                    used = 0.0
                else:
                    s.c.new_page()
                    s._page_head()
                    top = s.y + 6
                    ci, colx, coly, used = 0, MARGIN, top, 0.0
            n = sum(int(x.get("q") or 1) for x in items)
            c.text(colx, coly + 8, "%s (%d)" % (lab.upper(), n), 6.4, "B", INK, tracking=0.6)
            c.line(colx, coly + 11.5, colx + colw, coly + 11.5, INK, 0.5)
            yy = coly + 16
            for it in items:
                q = int(it.get("q") or 1)
                cost = str(it.get("c") or "").replace("}{", "").replace("{", "").replace("}", "") if it.get("c") else ""
                nm = str(it.get("n", ""))
                room = max_char - len(str(q)) - 1 - (len(cost) + 1 if cost else 0)
                if len(nm) > room:
                    nm = nm[: max(3, room - 1)] + "."
                c.text(colx, yy + 7, str(q), 7.2, "R", INK3)
                c.text(colx + (len(str(q)) + 1) * CHAR_W * 7.2, yy + 7, nm, 7.2, "R", INK)
                if cost:
                    c.text(colx + colw, yy + 7, cost, 6.6, "R", COBALT, align="right")
                yy += line_h
            coly = yy + 8
            used += hgt
        s.y = s.BOTTOM

    return s.finish("%s fact sheet" % name)
