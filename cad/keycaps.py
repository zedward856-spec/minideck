"""The HarukiToreda silicone cover (black, white legends) as display keycaps for the viewer.

Keycaps are made from the plate's key openings; legends follow the product photos (CardKB layout,
shifted symbols top-right, inverted white labels on Esc / Tab / Shift / Sym / fn).
"""
import _here  # noqa: F401  (repo root as the working dir)
import numpy as np, pyvista as pv, trimesh
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon
import base as B
from params import *

KEY_TOP = B.KB_Z + SILICONE_H                       # silicone key tops (0.75 mm proud of the plate)
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
ROWS = [  # back row first; (main legend, shifted legend)
    [("Esc", ""), ("1", "!"), ("2", "@"), ("3", "#"), ("4", "$"), ("5", "%"), ("6", "^"), ("7", "&"),
     ("8", "*"), ("9", "("), ("0", ")"), ("⌫", "")],
    [("Tab", ""), ("Q", "{"), ("W", "}"), ("E", "["), ("R", "]"), ("T", "/"), ("Y", "\\"), ("U", "|"),
     ("I", "~"), ("O", "'"), ("P", "\""), ("fn", "")],
    [("⇧", ""), ("A", ";"), ("S", ":"), ("D", "`"), ("F", "+"), ("G", "-"), ("H", "_"), ("J", "="),
     ("K", "?"), ("L", ""), ("↵", "")],
    [("Sym", ""), ("Z", ""), ("X", ""), ("C", ""), ("V", ""), ("B", ""), ("N", ""), ("M", ""),
     (",", "<"), (".", ">"), ("SPACE", "")],
]
INVERTED = {"Esc", "Tab", "⇧", "Sym", "fn"}

def openings():
    m = trimesh.load("out/_top_inplace.stl")
    s = m.section(plane_origin=[0, 0, B.TOP_Z - 0.6], plane_normal=[0, 0, 1])
    pp, _ = s.to_2D(to_2D=np.eye(4))
    holes = []
    for g in pp.polygons_full:
        for h in g.interiors:
            hp = Polygon(h)
            if 12.0 < hp.area < 60.0:                 # key openings (not screw holes / the logo)
                holes.append(hp)
    return holes

def _rgb(h):
    h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

def legend(main, sec, w, h, px=24, key="#161618", ink="#f0f0f0"):
    return pv.Texture(np.asarray(legend_image(main, sec, w, h, px, key, ink)))

def legend_image(main, sec, w, h, px=24, key="#161618", ink="#f0f0f0"):
    """Image for one key top: silicone colour `key`, legends in `ink` (inverted labels swap them)."""
    W, H = int(w * px), int(h * px)
    kc, ic = _rgb(key), _rgb(ink)
    im = Image.new("RGB", (W, H), kc); d = ImageDraw.Draw(im)
    big = len(main) == 1
    size = int(H * (0.52 if big else 0.30))
    f1 = ImageFont.truetype(FONT, size)
    while size > 6 and d.textbbox((0, 0), main, font=f1)[2] > W * (0.86 if main not in INVERTED else 0.72):
        size -= 1; f1 = ImageFont.truetype(FONT, size)          # long legends (SPACE) shrink to fit
    if main in INVERTED:
        tw, th = d.textbbox((0, 0), main, font=f1)[2:]
        bx = (W - tw) / 2 - H * 0.12; by = (H - th) / 2 - H * 0.12
        d.rounded_rectangle((bx, by, bx + tw + H * 0.24, by + th + H * 0.30), radius=H * 0.12, fill=ic)
        d.text(((W - tw) / 2, (H - th) / 2 - H * 0.04), main, font=f1, fill=kc)
    else:
        tw, th = d.textbbox((0, 0), main, font=f1)[2:]
        d.text(((W - tw) / 2 - (W * 0.08 if sec else 0), (H - th) / 2 - H * 0.06), main, font=f1, fill=ic)
        if sec:
            f2 = ImageFont.truetype(FONT, int(H * 0.26))
            d.text((W * 0.66, H * 0.06), sec, font=f2, fill=ic)
    return im

def build():
    """[(keycap mesh, None), (legend plane, texture), ...] in the case frame."""
    holes = openings()
    c = np.array([h.centroid.coords[0] for h in holes])
    arrows = [h for h in holes if h.area < 34.0]           # the arrow openings are smaller
    keys = [(h, p) for h, p in zip(holes, c) if h.area >= 34.0]
    ys = np.array([p[1] for _, p in keys])
    order = np.argsort(-ys)                            # back to front
    rows, cur, last = [], [], None
    for i in order:
        if last is not None and abs(ys[i] - last) > 3.0:
            rows.append(cur); cur = []
        cur.append(keys[i]); last = ys[i]
    rows.append(cur)
    out = []
    def cap(h, main, sec):
        top = h.buffer(-0.35, join_style=2)
        pts = np.array(top.exterior.coords)[:-1]
        poly = pv.PolyData(np.c_[pts, np.full(len(pts), KEY_TOP)], faces=[len(pts)] + list(range(len(pts))))
        body = poly.extrude((0, 0, -(KEY_TOP - B.WALL_TOP + 0.4)), capping=True)
        out.append((body, None))
        x0, y0, x1, y1 = top.bounds
        pl = pv.Plane(center=((x0 + x1) / 2, (y0 + y1) / 2, KEY_TOP + 0.02), direction=(0, 0, 1),
                      i_size=x1 - x0, j_size=y1 - y0)
        pl.texture_map_to_plane(origin=(x0, y0, KEY_TOP), point_u=(x1, y0, KEY_TOP), point_v=(x0, y1, KEY_TOP), inplace=True)
        out.append((pl, (main, sec, x1 - x0, y1 - y0)))          # legend spec; textured by the viewer
    for r, row in enumerate(rows):
        row = sorted(row, key=lambda t: t[1][0])
        labels = ROWS[r] if r < len(ROWS) else []
        for k, (h, _) in enumerate(row):
            main, sec = labels[k] if k < len(labels) else ("", "")
            cap(h, main, sec)
    if len(arrows) == 4:
        a = sorted(arrows, key=lambda h: h.centroid.y)
        down, up = a[0], a[-1]
        mid = sorted(a[1:3], key=lambda h: h.centroid.x)
        for h, s in ((up, "▲"), (down, "▼"), (mid[0], "◀"), (mid[1], "▶")):
            cap(h, s, "")
    return out, [len(r) for r in rows], len(arrows)

if __name__ == "__main__":
    o, rl, na = build()
    print("rows", rl, "arrows", na, "actors", len(o))
