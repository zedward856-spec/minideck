"""Your logo (LOGO['file'] svg) as a 2D shape, for engraving on any face."""
import os, re
from shapely.geometry import Polygon
from shapely.ops import unary_union
from shapely import affinity
from params import *


def logo_poly(width, cx=0.0, cy=0.0, angle=0.0, flip_v=True):
    """Filled logo shapes, `width` mm wide, centred on (cx, cy). flip_v: svg 'up' -> +v."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), LOGO["file"])
    polys = []
    for d in re.findall(r'<path[^>]*\sd="([^"]+)"', open(path).read()):
        for sub in re.split(r"[Zz]", d):
            nums = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", sub)]
            if len(nums) >= 6:
                polys.append(Polygon(list(zip(nums[0::2], nums[1::2]))).buffer(0))
    g = unary_union(polys)
    # the inner chevrons touch the frame at single points (point contacts make non-manifold edges).
    # Keep both sharp: nudge the chevron a hair away from the frame, so its tip stops just short of it
    # (a round bridge here used to blob over the two points)
    from shapely.ops import nearest_points
    from shapely.geometry import Point
    gap = 0.004 * (g.bounds[2] - g.bounds[0])              # ~0.04 mm on a 9 mm logo
    parts = list(g.geoms) if hasattr(g, "geoms") else [g]
    for i in range(len(parts)):
        for j in range(i + 1, len(parts)):
            if parts[i].distance(parts[j]) < 1e-6:
                a, _ = nearest_points(parts[i], parts[j])
                k = i if parts[i].area < parts[j].area else j      # the chevron, not the frame
                c = parts[k].centroid
                d = ((c.x - a.x) ** 2 + (c.y - a.y) ** 2) ** 0.5
                parts[k] = affinity.translate(parts[k], gap * (c.x - a.x) / d, gap * (c.y - a.y) / d)
    g = unary_union(parts)
    x0, y0, x1, y1 = g.bounds
    s = width / (x1 - x0)
    g = affinity.translate(g, -(x0 + x1) / 2, -(y0 + y1) / 2)
    g = affinity.scale(g, s, -s if flip_v else s, origin=(0, 0))
    g = affinity.rotate(g, angle, origin=(0, 0))
    return affinity.translate(g, cx, cy)
