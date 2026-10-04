"""Radxa ZERO 3W in its real colours (from Radxa's official STEP), placed exactly where the case's
official model sits, header pins dropped (not fitted), decimated for the web.

    python3 coloured_radxa.py  ->  models/coloured/radxa_zero3w.glb
"""
import _here  # noqa: F401  (repo root as the working dir)
import numpy as np, trimesh, pyvista as pv, itertools
from step2glb import load_coloured

STEP = "models/radxa3w_stp/radxa_zero_3w_3d.stp"
PLACED = "models/radxa_zero3w_official_placed.stl"
CAP = 2000                                         # faces per colour

def fit(parts, placed):
    """the flip + offset that lays the STEP onto the placed model (it sits upside down in the case)"""
    pq = trimesh.proximity.ProximityQuery(placed)
    allm = trimesh.util.concatenate([m for m, _ in parts]); S = allm.sample(3000)
    best = None
    for f in (np.diag([1, 1, 1]), np.diag([1, -1, -1]), np.diag([-1, 1, -1]), np.diag([-1, -1, 1])):
        off = np.zeros(3); off[:2] = placed.bounds[0][:2] - (allm.vertices @ f.T).min(0)[:2]
        for dz in np.arange(5, 35, 0.25):
            off[2] = dz
            s = np.mean(np.abs(pq.signed_distance(S[::6] @ f.T + off)) < 0.15)
            if best is None or s > best[0]:
                best = (s, f.copy(), off.copy())
    return best

def build():
    parts = load_coloured(STEP, tol=0.08)
    placed = trimesh.load(PLACED); pq = trimesh.proximity.ProximityQuery(placed)
    score, flip, off = fit(parts, placed)
    print(f"fit {score:.0%} of the surface (the rest is the unfitted header)")
    sc = trimesh.Scene()
    for i, (m, c) in enumerate(parts):
        m = m.copy(); m.vertices = m.vertices @ flip.T + off
        keep = np.abs(pq.signed_distance(m.triangles_center)) < 0.2
        if keep.sum() < 4:
            continue
        m = m.submesh([np.where(keep)[0]], append=True)
        n = len(m.faces)
        if n > CAP:
            p = pv.PolyData(m.vertices, np.c_[np.full(n, 3), m.faces].ravel()).decimate(1 - CAP / n)
            m = trimesh.Trimesh(p.points, p.faces.reshape(-1, 4)[:, 1:])
        m.visual.face_colors = [int(c[0] * 255), int(c[1] * 255), int(c[2] * 255), 255]
        sc.add_geometry(m, geom_name=f"c{i}")
    sc.export("models/coloured/radxa_zero3w.glb")
    print("faces", sum(len(g.faces) for g in sc.geometry.values()))

if __name__ == "__main__":
    build()
