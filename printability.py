"""Printability audit of every printed part, in its print orientation (the exported STLs).

    python3 printability.py   -> printability_report.md
Checks: closed solid, fits the bed, thin walls, fused gaps, floating islands (layer by layer),
unsupported flat overhangs too wide to bridge.
"""
import numpy as np, trimesh, warnings
from shapely.geometry import Polygon
from shapely.ops import unary_union
from scipy.cluster.hierarchy import fcluster, linkage
warnings.filterwarnings("ignore")

PARTS = ["bottom", "keyboard_top", "screen_front", "screen_back", "battery_door", "battery_lock_slider", "sd_guide",
         "box_hatch", "hinge_axle", "hinge_cap"]
BED = 256.0          # Bambu X1/P1 (A1 mini: 180)
NOZZLE, LAYER = 0.4, 0.2
MIN_WALL = 0.6       # thinner than ~1.5 lines prints badly / not at all
MIN_GAP = 0.3        # slots narrower than this fuse shut
MAX_BRIDGE = 12.0    # flat unsupported spans wider than this sag without support

def clusters(pts, d=2.0, min_n=4):
    if len(pts) < min_n:
        return []
    lab = fcluster(linkage(pts, "single"), d, "distance") if len(pts) > 1 else np.array([1])
    out = []
    for k in set(lab):
        s = pts[lab == k]
        if len(s) >= min_n:
            out.append((len(s), s.min(0), s.max(0)))
    return sorted(out, key=lambda t: -t[0])

def ray_dist(m, org, dirs):
    loc, ri, _ = m.ray.intersects_location(org, dirs, multiple_hits=False)
    d = np.full(len(org), np.inf)
    d[ri] = np.linalg.norm(loc - org[ri], axis=1)
    return d

def audit(name):
    m = trimesh.load(f"out/{name}.stl"); m.merge_vertices()
    m.apply_translation([0, 0, -m.bounds[0][2]])
    R = {"name": name, "issues": [], "notes": []}
    R["size"] = np.round(m.extents, 1)
    if not m.is_watertight:
        R["issues"].append("not a closed solid (slicer must repair it)")
    nb = len(m.split(only_watertight=False))
    if nb > 1:
        R["issues"].append(f"{nb} separate bodies in one file (loose pieces?)")
    if max(m.extents[:2]) > BED:
        R["issues"].append(f"bigger than the {BED:.0f} mm bed")
    n, a, c = m.face_normals, m.area_faces, m.triangles_center
    rng = np.random.default_rng(0)
    idx = rng.choice(len(m.faces), min(25000, len(m.faces)), replace=False, p=a / a.sum())
    # thin walls: inward rays
    org = c[idx] - n[idx] * 1e-3
    t = ray_dist(m, org, -n[idx])
    for cnt, lo, hi in clusters(org[t < MIN_WALL], 2.0, 6)[:6]:
        R["issues"].append(f"thin wall (<{MIN_WALL} mm, min {t[t < MIN_WALL].min():.2f}) x{lo[0]:.1f}-{hi[0]:.1f} y{lo[1]:.1f}-{hi[1]:.1f} z{lo[2]:.1f}-{hi[2]:.1f} ({cnt} samples)")
    # fused gaps: outward rays that hit the part again very soon
    org2 = c[idx] + n[idx] * 1e-3
    g = ray_dist(m, org2, n[idx])
    for cnt, lo, hi in clusters(org2[g < MIN_GAP], 2.0, 6)[:6]:
        R["issues"].append(f"gap narrower than {MIN_GAP} mm (will fuse) x{lo[0]:.1f}-{hi[0]:.1f} y{lo[1]:.1f}-{hi[1]:.1f} z{lo[2]:.1f}-{hi[2]:.1f} ({cnt} samples)")
    # islands: a slice region that overlaps nothing in the slice below starts in mid-air
    zs = np.arange(LAYER, m.extents[2], LAYER)
    prev = None
    islands = []
    for z in zs:
        s = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
        if s is None:
            prev = None; continue
        try:
            pp, _ = s.to_2D(to_2D=np.eye(4))
            polys = [p for p in pp.polygons_full if p.area > 0.05]
        except Exception:
            polys = []
        if prev is not None and z > LAYER * 1.5:
            for p in polys:
                if not p.buffer(0.3).intersects(prev):
                    islands.append((round(z, 1), p.bounds, round(p.area, 1)))
        prev = unary_union(polys) if polys else None
    for z, b, ar in islands[:6]:
        R["issues"].append(f"floating island starts at z={z} (area {ar} mm2) x{b[0]:.1f}-{b[2]:.1f} y{b[1]:.1f}-{b[3]:.1f} - needs support")
    # flat downward faces above the bed: bridges vs too-wide spans
    down = (n[:, 2] < -0.97) & (c[:, 2] > 0.15)
    if down.any():
        sub = m.submesh([np.where(down)[0]], append=True)
        for piece in sub.split(only_watertight=False):
            if piece.area < 4:
                continue
            P = unary_union([Polygon(tr[:, :2]).buffer(0.01) for tr in piece.triangles if Polygon(tr[:, :2]).area > 1e-6])
            if P.is_empty:
                continue
            # span = smallest support-to-support width ~ 2x the largest inscribed radius
            r = 0.0
            for step in (0.5, 1, 2, 3, 4, 5, 6, 8, 10, 15, 20):
                if P.buffer(-step).is_empty: break
                r = step
            span = 2 * r
            z = piece.vertices[:, 2].mean()
            b = P.bounds
            if span > MAX_BRIDGE:
                R["issues"].append(f"flat overhang ~{span:.0f} mm across at z={z:.1f} (x{b[0]:.0f}-{b[2]:.0f} y{b[1]:.0f}-{b[3]:.0f}) - too wide to bridge cleanly")
            elif span >= 4:
                R["notes"].append(f"bridge ~{span:.0f} mm at z={z:.1f} (x{b[0]:.0f}-{b[2]:.0f} y{b[1]:.0f}-{b[3]:.0f}) - fine")
    return R

if __name__ == "__main__":
    out = ["# Printability audit", "", f"nozzle {NOZZLE}, layer {LAYER}, bed {BED:.0f}; parts in their print orientation", ""]
    for nm in PARTS:
        R = audit(nm)
        st = "OK" if not R["issues"] else f"{len(R['issues'])} issue(s)"
        print(f"== {nm} {R['size']}: {st}")
        for i in R["issues"]: print("   !", i)
        for i in R["notes"][:3]: print("   .", i)
        out += [f"## {nm} - {st}", f"size {R['size'].tolist()} mm", ""] + [f"- **{i}**" for i in R["issues"]] + [f"- {i}" for i in R["notes"]] + [""]
    open("printability_report.md", "w").write("\n".join(out))
