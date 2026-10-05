"""Cosmetic engravings (no thickness added), all kept where the wall behind stays thick enough:
  front face   port labels above the stripes: charge bolt, USB, headphones
  left face    I / O beside the power switch, an "open" arrow beside the battery lock
  underside    a battery outline under the cell (+ / - ends, 18650 specs), an ID plate and a radio plate
               either side of the NFC mark (read with the deck turned over, like the NFC mark)
  lid back     a shallow hex texture around the big logo (left unpainted)

    import marks;  b -= marks.base_cut()   (base.py)      s -= marks.lid_cut()   (lid.py)
    python3 marks.py   -> previews/marks_*.png (2D previews of each face)
"""
import _here  # noqa: F401  (repo root as the working dir)
import os, math
import numpy as np
from shapely.geometry import Polygon, Point, LineString, box as sbox
from shapely.ops import unary_union
from shapely import affinity
from params import *
from nfc_mark import text, rrect, ring

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPTA = os.path.join(HERE, "models/CorptaDEMO.otf")
K = MARKS


# ------------------------------------------------------------------ where the wall is thick enough
def _solid_section(stl, axis, at):
    """the part's solid cross-section on the plane <axis> = at, as shapely in that plane's (u, v):
    front/back (axis 1): (x, z), sides (axis 0): (y, z), top/bottom (axis 2): (x, y)"""
    import trimesh
    if not os.path.exists(stl):
        return None
    m = trimesh.load(stl)
    n = [0, 0, 0]; n[axis] = 1
    o = [0, 0, 0]; o[axis] = at
    sec = m.section(plane_origin=o, plane_normal=n)
    if sec is None:
        return None
    p2, T = sec.to_2D()
    keep = {0: (1, 2), 1: (0, 2), 2: (0, 1)}[axis]
    def back(coords):
        c = np.c_[np.asarray(coords), np.zeros(len(coords)), np.ones(len(coords))] @ T.T
        return [(a, b) for a, b in c[:, keep]]
    polys = [Polygon(back(p.exterior.coords), [back(h.coords) for h in p.interiors]).buffer(0) for p in p2.polygons_full]
    return unary_union(polys)


def safe(design, stl, axis, at, keep=0.35):
    """clip a design to where the part is still solid `at` (= depth + the wall to leave), shrunk by `keep`"""
    s = _solid_section(stl, axis, at)
    return design if s is None else design.intersection(s.buffer(-keep, 16))


def _close(g, c=0.12):
    """merge slits a nozzle can't print"""
    return g.buffer(c, 16).buffer(-c, 16)


def _fit(t, w):
    b = t.bounds
    return affinity.scale(t, w / (b[2] - b[0]), w / (b[2] - b[0])) if b[2] - b[0] > w else t


def _at(g, u, v):
    b = g.bounds
    return affinity.translate(g, u - (b[0] + b[2]) / 2, v - (b[1] + b[3]) / 2)


# ------------------------------------------------------------------ icons (centred on 0, 0)
def bolt(h):
    p = Polygon([(-0.15, 1.0), (0.55, 1.0), (0.12, 0.18), (0.6, 0.18), (-0.45, -1.0), (-0.12, -0.1), (-0.6, -0.1)])
    return affinity.scale(p, h / 2.0, h / 2.0, origin=(0, 0))


def headphones(h, line=0.5):
    r = h * 0.42
    arc = Point(0, 0).buffer(r + line / 2, 48).difference(Point(0, 0).buffer(r - line / 2, 48))
    arc = arc.intersection(sbox(-h, -0.05, h, h))
    cup = rrect(line * 1.9, h * 0.5, line * 0.6)
    g = unary_union([arc, affinity.translate(cup, -r, -h * 0.18), affinity.translate(cup, r, -h * 0.18)])
    return _at(g, 0, 0)


def power_i(h, line=0.55, r=0.0):
    """a plain bar, its corners rounded by r"""
    return rrect(line, h, r) if r > 0 else sbox(-line / 2, -h / 2, line / 2, h / 2)


def power_o(h, line=0.5):
    return Point(0, 0).buffer(h / 2, 48).difference(Point(0, 0).buffer(h / 2 - line, 48))


def arrow_up(h, w):
    head = Polygon([(-w / 2, h * 0.1), (w / 2, h * 0.1), (0, h / 2)])
    stem = sbox(-w * 0.17, -h / 2, w * 0.17, h * 0.12)
    return unary_union([head, stem])


# ------------------------------------------------------------------ front: port labels (x, z)
def front_design():
    import layout as L
    f = K["front"]
    ports, rp = L.port_cutouts(), L.radxa_ports()
    zc, h = f["z"], f["h"]
    ux0, ux1 = ports["charger_usbc"][:2]
    # left to right: charger USB-C (charges the cell), Radxa USB-C 2.0 OTG (its power + OTG port; silkscreen
    # USB_OTG), Radxa USB-C 3.0 HOST (silkscreen USB3.0) - checked against Radxa's v1.11 board drawing
    out = [_at(text("PWR", h, bold=True), (ux0 + ux1) / 2, zc)]
    for k, lab in (("usbc_a", "PWR"), ("usbc_b", "DATA")):
        out.append(_at(text(lab, h, bold=True), sum(rp[k]) / 2, zc))
    out.append(_at(headphones(h * 1.25), ports["jack"][0], zc))
    return _close(unary_union(out))


# ------------------------------------------------------------------ left face: switch I/O, lock arrow (y, z)
def left_design():
    import switch as sw, battery_test as bt
    s = K["switch"]
    # beside the slot, at its height: 1 (ON, knob toward the back = your left seen from outside) and 0 (OFF,
    # toward the front = your right). They sit just outside the knob pocket, where the wall is full thickness.
    g = []
    a = K["lock"]
    a = K["lock"]
    lz0, lz1 = bt.LOCK_ZB, bt.LOCK_ZB + bt.LOCK_BODY[1]
    g.append(_at(arrow_up(a["h"], a["w"]), bt.LOCK_REC_Y1 + a["gap"] + a["w"] / 2, (lz0 + lz1) / 2 + a["up"]))
    return unary_union(g)


def switch_design():
    """a plain bar (1 = ON, knob toward the back = your left seen from outside) and a ring (0 = OFF, your right),
    right beside the fin slot. The wall there is the knob pocket's 0.7 mm skin, so these go in shallower."""
    import switch as sw
    s = K["switch"]
    sw_w = sw.slot_size()[0]
    y0, y1 = SWITCH["y"] - sw_w / 2, SWITCH["y"] + sw_w / 2
    bar, ring0 = power_i(s["h"], s["line"], s.get("round", 0.0)), power_o(s["h"], s["line"])
    return unary_union([_at(bar, y1 + s["gap"] + s["line"] / 2, sw.ZC),
                        _at(ring0, y0 - s["gap"] - s["h"] / 2, sw.ZC)])


def left_keepout():
    """stripes keep this far off the left-face marks"""
    return unary_union([left_design(), switch_design()]).buffer(K.get("stripe_gap", 1.0), 16)


# ------------------------------------------------------------------ underside (view coords, mirrored on placing)
def _under(design_view, xc, yc):
    """view coords (deck turned over, front edge toward you) -> case frame"""
    return affinity.translate(affinity.scale(design_view, -1, 1, origin=(0, 0)), xc, yc)


def battery_design():
    """battery outline under the cell: + at the cell's + end (inside, far from the door), - at the door end"""
    import battery_test as bt
    b = K["battery"]
    x0, x1 = bt.NEG_X + b["inset"], bt.SHOULDER_X - b["inset"]
    yc = b["y"]
    w, h, line = x1 - x0, b["h"], b["line"]
    # view coords: u = -(x - xc): the + end (high x) is on the LEFT when seen from below
    body = ring(w - 2.4, h, 1.8, line)
    nub = sbox(-w / 2 + 1.0, -h * 0.22, -w / 2 + 2.4 + line, h * 0.22)   # + terminal nub on the left (view), joined on
    g = [affinity.translate(body, 1.2, 0), nub]
    plus = unary_union([sbox(-1.6, -0.3, 1.6, 0.3), sbox(-0.3, -1.6, 0.3, 1.6)])
    minus = sbox(-1.6, -0.3, 1.6, 0.3)
    g.append(affinity.translate(plus, -w / 2 + 1.2 + 4.2, 0))
    g.append(affinity.translate(minus, w / 2 - 4.0, 0))
    inner = w - 2.4 - 2 * 8.5
    t1 = _fit(text("18650 · 3.7 V · PROTECTED", b["text_h"], bold=True), inner)
    t2 = _fit(text("BUTTON TOP · ≤ 70 mm", b["text_h"] * 0.8, bold=True), inner)
    g.append(_at(t1, 1.2, h * 0.17))
    g.append(_at(t2, 1.2, -h * 0.24))
    return _close(unary_union(g)), ((x0 + x1) / 2, yc)


def plate_designs():
    """ID plate and radio plate, each W x H, as (design_view, centre) pairs"""
    p = K["plates"]
    W, H = p["w"], p["h"]
    out = []
    # ID: logo, MINIDECK, build, maker
    from logo import logo_poly
    g = [ring(W, H, 1.6, p["line"])]
    v = H / 2 - 2.4
    lg = logo_poly(W * 0.42, 0, 0, flip_v=True)
    v -= (lg.bounds[3] - lg.bounds[1]) / 2
    g.append(_at(lg, 0, v)); v -= (lg.bounds[3] - lg.bounds[1]) / 2 + 2.0
    for s, hh, font in (("MINIDECK", p["title_h"], CORPTA), ("BUILD 001", p["text_h"], None),
                        ("2026", p["text_h"], None), (p.get("name", "sl01220"), p["text_h"], None)):
        t = _fit(text(s, hh, font, bold=True), W - 4.0)
        v -= (t.bounds[3] - t.bounds[1]) / 2
        g.append(_at(t, 0, v)); v -= (t.bounds[3] - t.bounds[1]) / 2 + p["gap"]
    body = unary_union(g[1:])                       # centre the content in its frame
    bb = body.bounds
    g = [g[0], affinity.translate(body, 0, -(bb[1] + bb[3]) / 2)]
    out.append((_close(unary_union(g)), p["id_xy"]))
    # radios: small label over each value
    g = [ring(W, H, 1.6, p["line"])]
    v = H / 2 - 2.6
    for lab, val in (("RTL-SDR", "25–1750 MHz"), ("LORA", "920 MHz"), ("GPS", "L1 1575 MHz"),
                     ("WI-FI · BT", "2.4 / 5 GHz"), ("POWER", "5 V · 2.6 A")):
        a = _fit(text(lab, p["label_h"], bold=True), W - 4.0)
        b = _fit(text(val, p["text_h"], bold=True), W - 4.0)
        v -= (a.bounds[3] - a.bounds[1]) / 2
        g.append(_at(a, 0, v)); v -= (a.bounds[3] - a.bounds[1]) / 2 + 0.9
        v -= (b.bounds[3] - b.bounds[1]) / 2
        g.append(_at(b, 0, v)); v -= (b.bounds[3] - b.bounds[1]) / 2 + p["gap"] + 0.6
    body = unary_union(g[1:])                       # centre the list in its frame (no empty band at the bottom)
    bb = body.bounds
    g = [g[0], affinity.translate(body, 0, -(bb[1] + bb[3]) / 2)]
    out.append((_close(unary_union(g)), p["rf_xy"]))
    return out


def under_poly():
    bd, (bx, by) = battery_design()
    parts = [_under(bd, bx, by)]
    for d, (xc, yc) in plate_designs():
        parts.append(_under(d, xc, yc))
    return unary_union(parts)


# ------------------------------------------------------------------ lid back: hex texture (x, y)
def lid_texture():
    import lid as Ld, cover
    t = K["texture"]
    s, line = t["cell"], t["line"]
    r = s / math.sqrt(3)                            # hexagon circumradius for flat-to-flat s
    cells = []
    xs = np.arange(-r * 2, OUT_W + r * 2, 1.5 * r)
    for i, x in enumerate(xs):
        for y in np.arange(-s, OUT_D + s, s):
            yy = y + (s / 2 if i % 2 else 0)
            hexa = Polygon([(x + r * math.cos(math.radians(60 * k)), yy + r * math.sin(math.radians(60 * k))) for k in range(6)])
            cells.append(hexa.exterior.buffer(line / 2, 4, join_style=2))
    grid = unary_union(cells)
    area = cover.outline().buffer(-t["edge"])
    area = area.intersection(sbox(0, 0, OUT_W, OUT_D - t["back"]))
    logo = Ld.logo_polygons()
    area = area.difference(logo.convex_hull.buffer(t["logo_gap"], 32))
    for x, y in getattr(Ld, "BEZEL_SCREWS", []):
        area = area.difference(Point(x, y).buffer(t["screw_gap"], 32))
    area = area.buffer(-0.01).buffer(0.01)
    # a clean border line round the textured area, so no cell just stops
    border = area.difference(area.buffer(-t["border"], 16)) if t.get("border") else Polygon()
    cut = unary_union([grid.intersection(area), border])
    # islands of plastic left too thin to print (where lines meet the border at a sharp angle): cut them too
    islands = area.difference(cut)
    thin = islands.difference(islands.buffer(-0.3, 8).buffer(0.3, 8))
    return unary_union([cut, thin.buffer(0.01)]).intersection(area)


# ------------------------------------------------------------------ solids
def _faces(poly):
    from build123d import Polyline, make_face
    geoms = list(poly.geoms) if hasattr(poly, "geoms") else [poly]
    out = []
    for g in geoms:
        if g.is_empty or g.area < 0.03:
            continue
        g = g.simplify(0.01)
        f = make_face(Polyline(*list(g.exterior.coords)[:-1], close=True))
        for h in g.interiors:
            if Polygon(h).area > 0.01:
                f -= make_face(Polyline(*list(h.coords)[:-1], close=True))
        out.append(f)
    return out


def _union(solids):
    u = None
    for s in solids:
        u = s if u is None else u + s
    return u


def xz_prism(poly, y0, y1):
    """front-view (x, z) polygon (holes kept) extruded from y0 to y1"""
    from build123d import Plane, extrude
    return _union([extrude(Plane.XZ.offset(-y1) * f, y1 - y0) for f in _faces(poly)])   # Plane.XZ faces -y


def yz_prism(poly, x0, x1):
    """side-view (y, z) polygon (holes kept) extruded from x0 to x1"""
    from build123d import Plane, extrude
    return _union([extrude(Plane.YZ.offset(x0) * f, x1 - x0) for f in _faces(poly)])


def xy_prism(poly, z0, z1):
    from build123d import Pos, extrude
    return _union([Pos(0, 0, z0) * extrude(f, z1 - z0) for f in _faces(poly)])


def base_polys():
    """(face, polygon, depth) for the case bottom, clipped to thick-enough wall"""
    d = K["depth"]
    stl = "out/bottom.stl"
    return [("front", safe(front_design(), stl, 1, d + K["wall"]), d),
            ("left", safe(left_design(), stl, 0, d + K["wall"]), d),
            ("left", safe(switch_design(), stl, 0, K["switch"]["depth"] + K["wall"], keep=0.05), K["switch"]["depth"]),
            ("under", safe(under_poly(), stl, 2, d + K["wall"]), d)]


def _prism(face, poly, a, b):
    if poly.is_empty:
        return None
    if face == "front":
        return xz_prism(poly, a, b)
    if face == "left":
        return yz_prism(poly, a, b)
    return xy_prism(poly, a, b)


def base_cut():
    if not K.get("enabled", True):
        return None
    return _union([s for s in (_prism(f, p, -1.0, dep) for f, p, dep in base_polys()) if s is not None])


def base_fill(e=0.04):
    return [s for s in (_prism(f, p, e, dep) for f, p, dep in base_polys()) if s is not None]


def lid_poly():
    import lid as Ld
    t = K["texture"]
    return safe(lid_texture(), "out/parts_in_place/screen_back.stl", 2, Ld.LID_TOP - t["depth"] - K["wall"])


def lid_cut():
    if not (K.get("enabled", True) and K["texture"].get("enabled", True)):
        return None
    import lid as Ld
    return xy_prism(lid_poly(), Ld.LID_TOP - K["texture"]["depth"], Ld.LID_TOP + 1.0)


def lid_fill(e=0.04):
    import lid as Ld
    if not (K.get("enabled", True) and K["texture"].get("enabled", True)):
        return []
    return [xy_prism(lid_poly(), Ld.LID_TOP - K["texture"]["depth"], Ld.LID_TOP - e)]


if __name__ == "__main__":
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    os.makedirs("previews", exist_ok=True)
    def draw(g, fn, title, bg="#2d2d2d", fg="#f7d116", flip=False):
        fig, ax = plt.subplots(figsize=(8, 6)); ax.set_facecolor(bg)
        g = affinity.scale(g, -1, 1, origin=(0, 0)) if flip else g
        for p in sorted((g.geoms if hasattr(g, "geoms") else [g]), key=lambda p: -p.envelope.area):
            x, y = p.exterior.xy; ax.fill(x, y, color=fg, lw=0)
            for h in p.interiors:
                x, y = h.xy; ax.fill(x, y, color=bg, lw=0)
        ax.set_aspect("equal"); ax.set_title(title); fig.savefig(fn, dpi=130, bbox_inches="tight"); plt.close(fig)
    polys = {}
    for f, p, _ in base_polys():
        polys[f] = p if f not in polys else polys[f].union(p)
    draw(polys["front"], "previews/marks_front.png", "front (x, z)")
    draw(polys["left"], "previews/marks_left.png", "left face seen from outside (-y right)", flip=True)
    draw(polys["under"], "previews/marks_under.png", "underside seen from below", flip=True)
    draw(lid_poly(), "previews/marks_lid.png", "lid back (x, y)", fg="#555555")
    for f, p in list(polys.items()) + [("lid", lid_poly())]:
        thin = p.buffer(-0.2)
        print(f"{f:6s} area {p.area:7.1f} mm2  pieces {len(getattr(p, 'geoms', [p]))}  "
              f"finer than 0.4 mm: {100 - thin.buffer(0.2).area / max(p.area, 1e-9) * 100:4.1f} %")
