"""The user's keyboard cover ('Keyboard Cover.stl'), used unchanged.

It goes over the keyboard flipped front-to-back (180 deg about X): that is the orientation in
which all 52 key openings line up with the keyboard in minideck.stl. The case outline is the
cover's outline.
"""
import os
import numpy as np
import trimesh
from shapely.geometry import Polygon, box as sbox
from build123d import Polyline, make_face, extrude, Pos

PARTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
COVER_FILE = os.path.join(PARTS_DIR, "Keyboard Cover.stl")
COVER_H = 5.99
_B = ((-56.0, 25.91, 0.0), (37.73, 90.0, 5.99))       # file bounds


def cover_in_case(cv_z0):
    m = trimesh.load(COVER_FILE)
    from params import KB_TURN
    t = np.eye(4)
    t[1, 1], t[2, 2] = -1, -1                           # flip front-to-back, face up
    if KB_TURN:                                         # ...and turned with the keyboard
        t[0, 0], t[1, 1] = -1, 1
    m.apply_transform(t)
    m.apply_translation(np.array([0.0, 0.0, cv_z0]) - m.bounds[0])
    return m


def outline(rounded_back=False):
    m = trimesh.load(COVER_FILE)
    s = m.section(plane_origin=[0, 0, 3.0], plane_normal=[0, 0, 1])
    p, _ = s.to_2D(to_2D=np.eye(4))
    g = max(p.polygons_full, key=lambda g: g.area)
    from params import KB_TURN
    if KB_TURN:
        pts = [(_B[1][0] - x, y - _B[0][1]) for x, y in g.exterior.coords]
    else:
        pts = [(x - _B[0][0], _B[1][1] - y) for x, y in g.exterior.coords]
    hull = Polygon(pts).convex_hull.simplify(0.02)     # wall has a gap for the Grove cable
    if not rounded_back:                                # back corners square: the deck runs
        x0, y0, x1, y1 = hull.bounds                    # straight into the hinge box behind
        hull = hull.union(sbox(x0, y1 - 6.0, x1, y1)).simplify(0.02)
    return hull


def face(poly, z=0.0):
    pts = list(poly.exterior.coords)[:-1]
    return Pos(0, 0, z) * make_face(Polyline(*[(x, y) for x, y in pts], close=True))


def prism(poly, z0, z1):
    parts = list(poly.geoms) if hasattr(poly, "geoms") else [poly]
    out = None
    for g in parts:
        if g.area < 0.5:
            continue
        s = extrude(face(Polygon(g.exterior), z0), z1 - z0)
        for h in g.interiors:
            if Polygon(h).area > 0.5:
                s -= extrude(face(Polygon(h), z0 - 0.1), z1 - z0 + 0.2)
        out = s if out is None else out + s
    return out
