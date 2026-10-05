"""Weak-spot check on the sliced parts (run cad/print_sim.py first): reads each part's G-code back as layers (drawn as
0.06 mm pixel images, so overlapping lines can't trip up the geometry) and flags
  - thin bridges carrying a feature: an area printed over air (not over the layer below, not over sparse infill),
    at least ~0.8 mm wide, whose roof is only 1-2 layers thick with more structure standing on it
    (the old switch-knob fin problem: a fin on a single bridged layer)
  - thin walls: islands only a single extrusion line wide that stand more than 1 mm tall

    python3 cad/print_layers_check.py   -> reports/print_layers_report.md (+ a summary on screen)
Results are cached per part (out/print_sim/<part>.weak.json) while its G-code is unchanged.
"""
import _here  # noqa: F401  (repo root as the working dir)
import os, glob, json, numpy as np
from scipy import ndimage
from PIL import Image, ImageDraw
from print_sim import parse, OUT

W = 0.42                      # extrusion width
R = 0.06                      # pixel size, mm


def disk(rad_mm):
    n = max(1, int(round(rad_mm / R)))
    y, x = np.ogrid[-n:n + 1, -n:n + 1]
    return x * x + y * y <= n * n


def layers(gcode):
    segs, _ = parse(gcode)
    segs = [s for s in segs if s[5] != "Skirt/Brim" and not s[5].startswith("Support")]
    a = np.array([s[:5] for s in segs])
    x0, y0 = a[:, [0, 2]].min() - 2, a[:, [1, 3]].min() - 2
    w = int((a[:, [0, 2]].max() + 2 - x0) / R) + 1
    h = int((a[:, [1, 3]].max() + 2 - y0) / R) + 1
    zs = sorted(set(np.round(a[:, 4], 3)))
    zi = {z: i for i, z in enumerate(zs)}
    imgs = [Image.new("1", (w, h)) for _ in zs]
    infs = [Image.new("1", (w, h)) for _ in zs]
    lw, iw = max(1, int(round(W * 1.15 / R))), int(round(4.0 / R))    # lines a bit wide so neighbours merge
    for (xa, ya, xb, yb, z), t in zip(a, (s[5] for s in segs)):
        k = zi[round(z, 3)]
        p = [((xa - x0) / R, (ya - y0) / R), ((xb - x0) / R, (yb - y0) / R)]
        ImageDraw.Draw(imgs[k]).line(p, fill=1, width=lw)
        if t == "Internal infill":
            ImageDraw.Draw(infs[k]).line(p, fill=1, width=iw)
    M = [np.array(im, bool) for im in imgs]
    INF = [np.array(im, bool) for im in infs]
    return zs, M, INF, (x0, y0)


def check(gcode):
    zs, M, INF, (x0, y0) = layers(gcode)
    lh = zs[1] - zs[0] if len(zs) > 1 else 0.2
    px = R * R
    bridges, walls = [], []
    grow_below, sliver, near = disk(W * 0.5), disk(0.35), disk(0.3)
    for n in range(1, len(zs)):
        U = M[n] & ~ndimage.binary_dilation(M[n - 1], grow_below)
        lab, cnt = ndimage.label(U)
        for i, sl in enumerate(ndimage.find_objects(lab), 1):
            u = lab[sl] == i
            a = u.sum() * px
            if a < 0.8 or not ndimage.binary_erosion(u, sliver).any():       # a sliver at a slope's edge
                continue
            if (INF[n - 1][sl] & u).sum() > 0.5 * u.sum():                   # bridging sparse infill: normal
                continue
            k = 1
            while n + k < len(zs) and (M[n + k][sl] & u).sum() > 0.8 * u.sum():
                k += 1
            on_top = (M[n + k][sl] & ndimage.binary_dilation(u, near)).sum() * px if n + k < len(zs) else 0
            if k <= 2 and on_top > 0.25:
                cy, cx = ndimage.center_of_mass(u)
                bridges.append((float(zs[n]), k, round(a, 2), round(float(on_top), 2),
                                (round(float(x0 + (sl[1].start + cx) * R), 1), round(float(y0 + (sl[0].start + cy) * R), 1))))
    # thin walls: islands that vanish when shrunk by 0.3 mm (a single line is ~0.48 wide here, two lines ~0.95)
    thin = []
    for n in range(len(zs)):
        lab, cnt = ndimage.label(M[n])
        t = np.zeros_like(M[n])
        for i, sl in enumerate(ndimage.find_objects(lab), 1):
            u = lab[sl] == i
            if u.sum() * px > 0.2 and not ndimage.binary_erosion(u, disk(0.3)).any():
                t[sl] |= u
        thin.append(t)
    done = np.zeros(M[0].shape, dtype=int)
    for n in range(len(zs)):
        lab, cnt = ndimage.label(thin[n] & (done <= n))
        for i, sl in enumerate(ndimage.find_objects(lab), 1):
            u = np.zeros_like(thin[n]); u[sl] = lab[sl] == i
            k, cur = 0, u
            while n + k < len(zs) and (thin[n + k] & cur).any():
                cur = thin[n + k] & ndimage.binary_dilation(cur, disk(0.3)); k += 1
            done[u] = n + k
            if k * lh > 1.0:
                cy, cx = ndimage.center_of_mass(u)
                walls.append((float(zs[n]), round(float(k * lh), 2), round(float(u.sum() * px), 2),
                              (round(float(x0 + cx * R), 1), round(float(y0 + cy * R), 1))))
    return lh, len(zs), bridges, walls


if __name__ == "__main__":
    L = ["# Weak-spot check on the sliced parts", "",
         "From the G-code of `cad/print_sim.py`, each layer drawn as a 0.06 mm pixel image. **Thin bridge carrying a "
         "feature** = an area printed over air (not over the layer below or sparse infill) whose roof is only 1-2 "
         "layers thick with more structure standing on it. **Thin wall** = a single extrusion line wide and taller than "
         "1 mm. Positions are on the print bed (mm, the part centred at 128, 128).", ""]
    summary = []
    for g in sorted(glob.glob(f"{OUT}/*.gcode")):
        name = os.path.basename(g)[:-6]
        cache = g[:-6] + ".weak.json"
        if os.path.exists(cache) and os.path.getmtime(cache) > os.path.getmtime(g):
            lh, nl, br, wl = json.load(open(cache))
        else:
            lh, nl, br, wl = check(g)
            json.dump([lh, nl, br, wl], open(cache, "w"))
        summary.append((name, len(br), len(wl)))
        L += [f"## {name}", "", f"{nl} layers of {lh:.2f} mm.", ""]
        if not br and not wl:
            L += ["No weak spots.", ""]
        for z, k, a, on, c in br:
            L.append(f"- **thin bridge carrying a feature** at z {z:.2f} mm, around {tuple(c)}: {a} mm² printed over "
                     f"air, roof only {k} layer(s) thick, {on} mm² of structure standing on it")
        for z, h, a, c in wl:
            L.append(f"- thin wall from z {z:.2f} mm, {h} mm tall, around {tuple(c)} ({a} mm² per layer)")
        L.append("")
    os.makedirs("reports", exist_ok=True)
    open("reports/print_layers_report.md", "w").write("\n".join(L) + "\n")
    for n, b, w in summary:
        print(f"{n:24s} thin bridges carrying a feature: {b:2d}   thin walls: {w:2d}")
