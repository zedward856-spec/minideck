"""Engraved hazard-stripe bands round the base and the lid (settings: SIDE_STRIPES in params.py)."""
import math
from shapely.geometry import Polygon, box as sbox
from shapely.ops import unary_union
from params import *


def segments():
    """(part, face, u0, u1, lean) for every stripe patch."""
    s = SIDE_STRIPES
    if s.get("segments"):
        return list(s["segments"])
    import base as B, battery_test as bt, lid as Ld
    e, mid = s["edge"], OUT_W / 2
    out = []
    # base: right side, back, front all the way; left side split round the battery door + lock
    out += [("bottom", "right", e, B.BOX_BACK - e, +1),
            ("bottom", "left", e, B.BOX_BACK - e, +1),
            ("bottom", "front", e, OUT_W - e, -1),        # one run each, same lean all the way
            ("bottom", "back", e, OUT_W - e, +1)]
    # lid: both sides full length, front from each corner in to the text
    out += [("lid", "left", e, OUT_D - 2.0, +1), ("lid", "right", e, OUT_D - 2.0, +1)]
    tc = Ld.lid_text_cut() if LID_TEXT.get("face") == "front" else None
    if tc is not None:
        bb = tc.bounding_box()
        out += [("lid", "front", e, bb.min.X - s["text_gap"], -1),
                ("lid", "front", bb.max.X + s["text_gap"], OUT_W - e, -1)]
    else:
        out += [("lid", "front", e, OUT_W - e, -1)]
    return out


def keepouts(part, face):
    """Holes, recesses and doors on a face, grown by hole_gap, in that face's (u, z)."""
    if part != "bottom":
        return None
    from shapely.geometry import Point
    import base as B, battery_test as bt, layout as L
    g = []
    if face == "front":
        ports, rp = L.port_cutouts(), L.radxa_ports()
        ux0, ux1, uz0, uz1, _ = ports["charger_usbc"]
        centres = [((ux0 + ux1) / 2, (uz0 + uz1) / 2)] + \
                  [(sum(rp[k]) / 2, sum(rp["z"]) / 2) for k in ("usbc_a", "usbc_b")]
        w, h = B.USB_RECESS[0], B.USB_RECESS[1]
        g += [sbox(xc - w / 2, zc - h / 2, xc + w / 2, zc + h / 2) for xc, zc in centres]
        jx, jz, _ = ports["jack"]
        g.append(Point(jx, jz).buffer(B.JACK_RECESS[0] / 2, 64))
    elif face == "left":
        g.append(sbox(bt.HY - bt.KR - 1.1, B.FLOOR, bt.REC_Y1, bt.REC_Z1))          # battery door
        g.append(sbox(bt.REC_Y1, bt.LOCK_ZB - 0.2, bt.LOCK_REC_Y1,                  # lock slider
                      bt.LOCK_ZB + bt.LOCK_TRAVEL + bt.LOCK_BODY[1] + 0.2))
        import switch as sw                                                          # power switch knob
        kl, kh = SWITCH["knob"][:2]                                                 # (knob pocket behind the fin slot)
        half = (kl + SWITCH["travel"]) / 2 + 0.4
        g.append(sbox(SWITCH["y"] - half, sw.ZC - kh / 2 - 0.3, SWITCH["y"] + half, sw.ZC + kh / 2 + 0.3))
    return unary_union(g).buffer(SIDE_STRIPES["hole_gap"], 32) if g else None


def patch_polygon(u0, u1, z0, z1, lean, avoid=None, part=None):
    """Slanted bars clipped to a band with slightly rounded ends, in (u, z)."""
    s = dict(SIDE_STRIPES)
    s.update({k: v for k, v in SIDE_STRIPES.get(part, {}).items() if k in ("bar", "gap")})
    h = z1 - z0
    sh = lean * h * math.tan(math.radians(s["slant"]))
    pitch = s["bar"] + s["gap"]
    bars, u = [], u0 - abs(sh) - pitch
    while u < u1 + abs(sh) + pitch:
        bars.append(Polygon([(u, z0), (u + s["bar"], z0), (u + s["bar"] + sh, z1), (u + sh, z1)]))
        u += pitch
    r = s["corner_r"]
    band = sbox(u0, z0, u1, z1).buffer(-r).buffer(r) if r > 0 else sbox(u0, z0, u1, z1)
    if avoid is not None:
        band = band.difference(avoid)
    p = unary_union(bars).intersection(band)
    t = s.get("tip_r", 0)
    return p.buffer(-t).buffer(t) if t > 0 else p


def _xz_prism(poly, y0, y1):
    from build123d import Plane, Polyline, make_face, extrude
    out = None
    for g in (poly.geoms if hasattr(poly, "geoms") else [poly]):
        if g.area < 0.05:
            continue
        f = make_face(Polyline(*list(g.exterior.coords)[:-1], close=True))
        sld = extrude(Plane.XZ.offset(-y1) * f, y1 - y0)      # Plane.XZ faces -y
        out = sld if out is None else out + sld
    return out


def stripes_cut(part):
    """Solid to subtract from 'bottom' or 'lid' (None if disabled)."""
    s = SIDE_STRIPES
    if not s.get("enabled", True):
        return None
    from base import yz_prism, BOX_BACK
    d = s["depth"]
    z0, z1 = s[part]["z0"], s[part]["z1"]
    cut = None
    for prt, face, u0, u1, lean in segments():
        if prt != part or u1 - u0 < 3:
            continue
        poly = patch_polygon(u0, u1, z0, z1, lean, keepouts(part, face), part)
        if poly.is_empty:
            continue
        if face == "left":
            c = yz_prism(poly, -1.0, d)
        elif face == "right":
            c = yz_prism(poly, OUT_W - d, OUT_W + 1.0)
        elif face == "front":
            c = _xz_prism(poly, -1.0, d)
        else:
            c = _xz_prism(poly, BOX_BACK - d, BOX_BACK + 1.0)
        cut = c if cut is None else cut + c
    return cut
