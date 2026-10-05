"""Print simulation: slice every print file with PrusaSlicer (CLI), read the G-code back and show how each part is
built layer by layer - walls, infill, top/bottom skin, bridges, supports - plus layers, time and filament.

    python3 cad/print_sim.py            -> docs/print-sim/  (README.md, <part>.png, <part>_build.gif, <part>_layers.png)
    python3 cad/print_sim.py bottom     -> just one part (by its print/ file name)

PrusaSlicer 2.8.1 (~/Apps/prusaslicer/squashfs-root/AppRun) with a Bambu-like machine (256 mm bed, 0.4 nozzle, PLA,
fast motion limits); Bambu's own slicer will differ a little in times. G-code goes to out/print_sim/ (not in git).
"""
import _here  # noqa: F401  (repo root as the working dir)
import os, re, sys, subprocess, numpy as np

SLICER = os.path.expanduser("~/Apps/prusaslicer/squashfs-root/AppRun")
OUT, DOC = "out/print_sim", "docs/print-sim"
from export_print import PARTS, COLOURS

# per part: layer height and extras (from print/README.md)
LAYER = {"keyboard_plate": 0.12, "screen_bezel": 0.12, "battery_lock_clip": 0.12, "torque_hinge_cap": 0.12,
         "hinge_axle": 0.12, "switch_knob": 0.12}
EXTRA = {"battery_door": dict(brim_width=5), "battery_door_fit_test": dict(brim_width=3)}

BASE = dict(   # a Bambu-like PLA setup
    bed_shape="0x0,256x0,256x256,0x256", max_print_height=250, nozzle_diameter=0.4, filament_diameter=1.75,
    printer_technology="FFF", gcode_flavor="marlin2", use_relative_e_distances=1,
    temperature=220, first_layer_temperature=220, bed_temperature=55, first_layer_bed_temperature=55,
    filament_density=1.24, filament_cost=20, filament_type="PLA",
    perimeters=2, top_solid_layers=5, bottom_solid_layers=3, fill_density="15%", fill_pattern="grid",
    top_fill_pattern="monotonic", bottom_fill_pattern="monotonic", infill_anchor=0,
    first_layer_height=0.2, extrusion_width=0.42, first_layer_extrusion_width=0.5,
    perimeter_speed=200, external_perimeter_speed=150, infill_speed=250, solid_infill_speed=180,
    top_solid_infill_speed=120, bridge_speed=50, gap_fill_speed=100, first_layer_speed=50, travel_speed=500,
    small_perimeter_speed=100, support_material_speed=150,
    default_acceleration=10000, perimeter_acceleration=5000, infill_acceleration=10000,
    first_layer_acceleration=500, travel_acceleration=10000, bridge_acceleration=2000,
    machine_limits_usage="time_estimate_only",
    machine_max_acceleration_x=20000, machine_max_acceleration_y=20000, machine_max_acceleration_extruding=20000,
    machine_max_feedrate_x=500, machine_max_feedrate_y=500, machine_max_feedrate_z=20,
    machine_max_jerk_x=9, machine_max_jerk_y=9,
    support_material=0, brim_width=0, skirts=0, gcode_comments=0, gcode_label_objects="firmware",
    layer_gcode="G92 E0",
)

TYPES = [  # PrusaSlicer ;TYPE: name -> (label, colour)
    ("External perimeter", "outer wall", "#f7d116"), ("Perimeter", "inner wall", "#f08c00"),
    ("Overhang perimeter", "overhang wall", "#2f9e44"), ("Internal infill", "infill", "#c2255c"),
    ("Solid infill", "solid infill", "#7048e8"), ("Top solid infill", "top skin", "#e03131"),
    ("Bridge infill", "bridge", "#1c7ed6"), ("Gap fill", "gap fill", "#ffffff"),
    ("Skirt/Brim", "brim", "#20c997"), ("Support material", "support", "#adb5bd"),
    ("Support material interface", "support interface", "#495057")]
TCOL = {t: c for t, _, c in TYPES}
TLAB = {t: l for t, l, _ in TYPES}


def ini(path, **kw):
    with open(path, "w") as f:
        for k, v in {**BASE, **kw}.items():
            f.write(f"{k} = {v}\n")


def slice_part(name, stl, layer, extra):
    os.makedirs(OUT, exist_ok=True)
    cfg = f"{OUT}/{name}.ini"
    ini(cfg, layer_height=layer, **extra)
    g = f"{OUT}/{name}.gcode"
    r = subprocess.run([SLICER, "--export-gcode", "--load", cfg, "--center", "128,128", "--output", g, stl],
                       capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(g):
        raise RuntimeError(f"slicing {name} failed:\n{r.stdout[-800:]}\n{r.stderr[-800:]}")
    return g


def parse(gcode):
    """extrusion segments: list of (x0, y0, x1, y1, z, type) + stats from the footer"""
    segs, stats = [], {}
    x = y = z = 0.0
    typ = None
    for line in open(gcode):
        if line.startswith(";TYPE:"):
            typ = line[6:].strip(); continue
        if line.startswith(";Z:"):
            z = float(line[3:]); continue
        if line.startswith("; "):
            m = re.match(r"; (estimated printing time \(normal mode\)|filament used \[g\]|filament used \[mm\]|"
                         r"filament used \[cm3\]) = (.+)", line)
            if m:
                stats[m.group(1)] = m.group(2).strip()
            continue
        if line.startswith("G1 ") or line.startswith("G0 "):
            nx, ny, e = x, y, None
            for tok in line.split()[1:]:
                c = tok[0]
                if c == "X": nx = float(tok[1:])
                elif c == "Y": ny = float(tok[1:])
                elif c == "Z": z = float(tok[1:])
                elif c == "E": e = float(tok[1:])
            if e is not None and e > 0 and (nx != x or ny != y) and typ:
                segs.append((x, y, nx, ny, z, typ))
            x, y = nx, ny
    return segs, stats


def hms(s):
    """'1h 2m 3s' -> minutes"""
    t = 0
    for v, u in re.findall(r"(\d+)([dhms])", s):
        t += int(v) * {"d": 1440, "h": 60, "m": 1, "s": 1 / 60}[u]
    return t


def render(name, segs, layer):
    import pyvista as pv
    from PIL import Image
    a = np.array([(s[0], s[1], s[4], s[2], s[3], s[4]) for s in segs], float)
    types = [s[5] for s in segs]
    zs = np.unique(np.round(a[:, 2], 3))
    pts = np.vstack([a[:, :3], a[:, 3:]])
    n = len(a)
    lines = np.hstack([np.full((n, 1), 2), np.c_[np.arange(n), np.arange(n) + n]]).ravel()
    cols = np.array([[int(TCOL.get(t, "#888888")[i:i + 2], 16) for i in (1, 3, 5)] for t in types], np.uint8)
    poly = pv.PolyData(pts, lines=lines)
    poly.cell_data["rgb"] = cols
    ctr = pts.mean(0); ext = np.ptp(pts, 0)
    d = max(ext[0], ext[1], ext[2] * 1.5) * 1.75 + 6

    def shot(mesh, fn, size=(1000, 760)):
        p = pv.Plotter(off_screen=True, window_size=size)
        p.set_background("#0f0f12")
        p.add_mesh(mesh, scalars="rgb", rgb=True, line_width=2.2)
        p.camera_position = [(ctr[0] + d * 0.62, ctr[1] - d * 0.78, ctr[2] + d * 0.62), tuple(ctr), (0, 0, 1)]
        img = p.screenshot(fn, return_img=True)
        p.close()
        return img

    os.makedirs(DOC, exist_ok=True)
    shot(poly, f"{DOC}/{name}.png")
    # build-up animation: the part growing layer by layer
    frames = []
    for k in np.linspace(max(1, len(zs) // 24), len(zs), 24).astype(int):
        zc = zs[min(k, len(zs)) - 1]
        keep = np.where(a[:, 2] <= zc + 1e-6)[0]
        sub = poly.extract_cells(keep)
        frames.append(Image.fromarray(shot(sub, None, (640, 486))))
    frames += [frames[-1]] * 6
    frames[0].save(f"{DOC}/{name}_build.gif", save_all=True, append_images=frames[1:], duration=140, loop=0, optimize=True)
    # a few layers seen from above
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    picks = sorted(set([zs[0], zs[len(zs) // 3], zs[(2 * len(zs)) // 3], zs[-1]]))
    fig, axs = plt.subplots(1, len(picks), figsize=(4.2 * len(picks), 4.4), facecolor="#0f0f12")
    for ax, zc in zip(np.atleast_1d(axs), picks):
        m = np.abs(a[:, 2] - zc) < 1e-6
        ax.add_collection(LineCollection(np.stack([a[m][:, :2], a[m][:, 3:5]], 1),
                                         colors=[TCOL.get(types[i], "#888") for i in np.where(m)[0]], linewidths=0.7))
        ax.set_xlim(pts[:, 0].min() - 2, pts[:, 0].max() + 2); ax.set_ylim(pts[:, 1].min() - 2, pts[:, 1].max() + 2)
        ax.set_aspect("equal"); ax.axis("off")
        ax.set_title(f"layer {int(np.searchsorted(zs, zc)) + 1} / {len(zs)}  ·  z {zc:.2f} mm", color="#ddd", fontsize=10)
    fig.savefig(f"{DOC}/{name}_layers.png", dpi=110, bbox_inches="tight", facecolor="#0f0f12")
    plt.close(fig)
    return len(zs), sorted(set(types), key=lambda t: [x[0] for x in TYPES].index(t) if t in TCOL else 99)


def legend_png():
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(9, 0.9), facecolor="#0f0f12"); ax.axis("off")
    for i, (_, lab, c) in enumerate(TYPES):
        ax.add_patch(plt.Rectangle((i % 6 * 1.5, -(i // 6) * 0.5), 0.25, 0.25, color=c))
        ax.text(i % 6 * 1.5 + 0.35, -(i // 6) * 0.5 + 0.12, lab, color="#ddd", va="center", fontsize=9)
    ax.set_xlim(-0.1, 9); ax.set_ylim(-0.7, 0.4)
    fig.savefig(f"{DOC}/legend.png", dpi=110, bbox_inches="tight", facecolor="#0f0f12"); plt.close(fig)


if __name__ == "__main__":
    args = sys.argv[1:]
    report_only = "--report" in args          # rebuild README.md from the existing G-code (no slicing / rendering)
    only = {a for a in args if not a.startswith("--")}
    rows = []
    for src, folder, name, qty, note in PARTS:
        if only and name not in only:
            continue
        stl = f"print/{folder}/{name}.stl"
        layer = LAYER.get(name, 0.2)
        if report_only:
            g = f"{OUT}/{name}.gcode"
            segs, st = parse(g)
            nl = len(set(round(sg[4], 3) for sg in segs))
            types = sorted(set(sg[5] for sg in segs), key=lambda t: [x[0] for x in TYPES].index(t) if t in TCOL else 99)
        else:
            g = slice_part(name, stl, layer, EXTRA.get(name, {}))
            segs, st = parse(g)
            nl, types = render(name, segs, layer)
        rows.append(dict(name=name, folder=folder, note=note, layer=layer, layers=nl, types=types,
                         time=st.get("estimated printing time (normal mode)", "?"),
                         grams=float(st.get("filament used [g]", "0").split(",")[0]),
                         metres=float(st.get("filament used [mm]", "0").split(",")[0]) / 1000))
        print(f"{name:24s} {layer} mm  {nl:4d} layers  {rows[-1]['time']:>10s}  {rows[-1]['grams']:6.1f} g")
    if only and not report_only:
        sys.exit()
    legend_png()
    L = ["# Print simulation", "",
         "Every print file sliced with PrusaSlicer 2.8.1 (Bambu-like PLA setup: 0.4 nozzle, 2 walls, 15 % grid infill, "
         "5 top / 3 bottom layers, fast motion limits) and read back layer by layer. Colours show what each line is. "
         "Times are estimates; Bambu Studio will differ a little. Re-run: `python3 cad/print_sim.py`.", "",
         "![legend](legend.png)", "", "## Totals", "",
         "| Filament | Parts | Time | Filament |", "|---|---|---|---|"]
    for folder in ("charcoal", "dark-grey", "yellow", "tests"):
        rs = [r for r in rows if r["folder"] == folder]
        if not rs:
            continue
        mins = sum(hms(r["time"]) for r in rs)
        L.append(f"| {COLOURS[folder][0]} | {len(rs)} | {int(mins // 60)} h {int(mins % 60)} min | "
                 f"{sum(r['grams'] for r in rs):.0f} g ({sum(r['metres'] for r in rs):.1f} m) |")
    real = [r for r in rows if r["folder"] != "tests"]
    mins = sum(hms(r["time"]) for r in real)
    L += [f"| **whole deck** (without the test piece) | {len(real)} | **{int(mins // 60)} h {int(mins % 60)} min** | "
          f"**{sum(r['grams'] for r in real):.0f} g** |", "", "## Parts", ""]
    for r in rows:
        L += [f"### {r['name']}  ·  {r['folder']}", "",
              f"{r['layer']} mm layers · **{r['layers']} layers** · **{r['time']}** · {r['grams']:.1f} g "
              f"({r['metres']:.2f} m) · {r['note']}", "",
              f"![{r['name']}]({r['name']}.png) ![{r['name']} printing]({r['name']}_build.gif)", "",
              f"![{r['name']} layers]({r['name']}_layers.png)", "",
              "Has: " + ", ".join(TLAB.get(t, t) for t in r["types"]), ""]
    open(f"{DOC}/README.md", "w").write("\n".join(L) + "\n")
    print("wrote", f"{DOC}/README.md")
