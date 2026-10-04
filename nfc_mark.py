"""NFC mark engraved into the underside of the case, right under the PN532: the board's outline, its antenna
coil (a rounded spiral), a big NFC with a wave icon, and its specs. Reads correctly with the deck turned over
(front edge toward you) and doubles as the "tap here" spot.

    import nfc_mark; b -= nfc_mark.cut()        (in base.py)
    python3 nfc_mark.py   -> previews/nfc_mark.png (2D preview)
"""
import os, numpy as np
from shapely.geometry import Polygon, Point, box as sbox
from shapely.ops import unary_union
from shapely import affinity
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties
from params import *

HERE = os.path.dirname(os.path.abspath(__file__))
M = NFC_MARK

def _pn_bounds():
    import layout as L
    b = L.bounds("pn532")
    return b[0], b[1], b[3], b[4]                       # x0, y0, x1, y1 (case frame)

def text(s, height, font=None, bold=False):
    """text outline as shapely, its cap height = `height` mm, centred on (0, 0) (view coords)"""
    fp = FontProperties(fname=font) if font else FontProperties(family="DejaVu Sans", weight="bold" if bold else "normal")
    tp = TextPath((0, 0), s, size=10, prop=fp)
    shape = Polygon()
    for ring in tp.to_polygons():
        if len(ring) >= 3:
            shape = shape.symmetric_difference(Polygon(ring).buffer(0))   # even-odd: glyph holes stay holes
    ref = TextPath((0, 0), "H", size=10, prop=fp).get_extents()
    k = height / max(ref.height, 1e-6)
    shape = affinity.scale(shape, k, k, origin=(0, 0))
    x0, y0, x1, y1 = shape.bounds
    return affinity.translate(shape, -(x0 + x1) / 2, -(y0 + y1) / 2)

def rrect(w, h, r):
    return sbox(-w / 2 + r, -h / 2 + r, w / 2 - r, h / 2 - r).buffer(r, 32)

def ring(w, h, r, line):
    """a rounded-rectangle line `line` mm wide, outer size w x h"""
    return rrect(w, h, r).difference(rrect(w - 2 * line, h - 2 * line, max(r - line, 0.05)))

def design():
    """the whole mark in view coords (u right, v away from you, deck upside down, front edge toward you)"""
    x0, y0, x1, y1 = _pn_bounds()
    W, H = x1 - x0 - 2 * M["inset"], y1 - y0 - 2 * M["inset"]
    line, pitch = M["line"], M["pitch"]
    parts = [ring(W, H, 2.0, line)]                                            # the board's outline
    cw, ch = W - 2 * M["coil_gap"], H - 2 * M["coil_gap"]
    for k in range(M["turns"]):                                                # antenna coil: turns + feed
        w, h = cw - 2 * k * pitch, ch - 2 * k * pitch
        r = ring(w, h, max(3.0 - k * pitch * 0.5, 0.8), line)
        gap = sbox(w / 2 - line - 0.2, -1.2 - k * 0.0, w / 2 + 0.2, 1.2)      # break on the right side ...
        parts.append(r.difference(gap))
        if k < M["turns"] - 1:                                                 # ... joined to the next turn in
            parts.append(sbox(w / 2 - line - pitch, 1.2 - line, w / 2, 1.2))
    inner_w = cw - 2 * M["turns"] * pitch
    inner_h = ch - 2 * M["turns"] * pitch
    corpta = os.path.join(HERE, "models/CorptaDEMO.otf")
    nfc = text("NFC", M["nfc_h"], corpta)
    waves = unary_union([Point(0, 0).buffer(r + 0.3, 48).difference(Point(0, 0).buffer(r - 0.3, 48)) for r in (1.4, 2.7, 4.0)])
    waves = waves.intersection(Polygon([(0, 0), (6, 4.6), (6, -4.6)])).union(Point(0, 0).buffer(0.6, 32))
    nb = nfc.bounds
    top = inner_h / 2 - 2.0 - (nb[3] - nb[1]) / 2
    gap_nfc = 1.6
    tw = (nb[2] - nb[0]) + gap_nfc + 5.0
    parts.append(affinity.translate(nfc, -tw / 2 + (nb[2] - nb[0]) / 2, top))
    parts.append(affinity.translate(waves, -tw / 2 + (nb[2] - nb[0]) + gap_nfc, top))
    v = top - (nb[3] - nb[1]) / 2 - 2.2
    for s, hgt in M["lines"]:
        t = text(s, hgt, bold=True)
        tb = t.bounds
        if tb[2] - tb[0] > inner_w - 2.0:                                     # shrink to fit inside the coil
            k = (inner_w - 2.0) / (tb[2] - tb[0]); t = affinity.scale(t, k, k); tb = t.bounds
        v -= (tb[3] - tb[1]) / 2
        t = t.buffer(M.get("close", 0.0), 16).buffer(-M.get("close", 0.0), 16)   # merge gaps a nozzle can't print
        parts.append(affinity.translate(t, 0, v))
        v -= (tb[3] - tb[1]) / 2 + 1.4
    return unary_union(parts)

def case_poly():
    """the design placed under the PN532 in the case frame (mirrored, as the underside is seen from below)"""
    x0, y0, x1, y1 = _pn_bounds()
    xc, yc = (x0 + x1) / 2, (y0 + y1) / 2
    d = affinity.scale(design(), -1, 1, origin=(0, 0))
    return affinity.translate(d, xc, yc)

def solid(z0, z1):
    from build123d import Polyline, make_face, extrude, Pos, Face, Wire
    from cover import prism
    parts = []
    poly = case_poly()
    geoms = list(poly.geoms) if hasattr(poly, "geoms") else [poly]
    out = None
    for g in geoms:
        if g.area < 0.05:
            continue
        ext = [(x, y) for x, y in list(g.exterior.coords)[:-1]]
        f = make_face(Polyline(*ext, close=True))
        for hole in g.interiors:
            f -= make_face(Polyline(*[(x, y) for x, y in list(hole.coords)[:-1]], close=True))
        s = Pos(0, 0, z0) * extrude(f, z1 - z0)
        out = s if out is None else out + s
    return out

def cut():
    return solid(-1.0, M["depth"])

if __name__ == "__main__":
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    d = design()
    fig, ax = plt.subplots(figsize=(6, 6)); ax.set_facecolor("#2d2d2d")
    for g in sorted((d.geoms if hasattr(d, "geoms") else [d]), key=lambda g: -g.envelope.area):   # big first
        x, y = g.exterior.xy; ax.fill(x, y, color="#f7d116", lw=0)
        for h in g.interiors:
            x, y = h.xy; ax.fill(x, y, color="#2d2d2d", lw=0)
    ax.set_aspect("equal"); ax.axis("off")
    os.makedirs("previews", exist_ok=True)
    fig.savefig("previews/nfc_mark.png", dpi=150, bbox_inches="tight", facecolor="#2d2d2d")
    thin = d.buffer(-M["line"] * 0.45)
    print("parts", len(d.geoms) if hasattr(d, "geoms") else 1, "area", round(d.area, 1), "mm2",
          "| survives a 0.45 mm erosion:", round(thin.area / d.area * 100), "% (rest is finer than the line width)")
