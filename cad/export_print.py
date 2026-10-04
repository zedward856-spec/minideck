"""Collect the print files into print/, one folder per filament colour (one batch per folder), each part
flat on the bed (z = 0) and centred, plus print/README.md with quantities and settings.

    python3 cad/export_print.py      (after battery_test.py / base.py / lid.py)
"""
import _here  # noqa: F401  (repo root as the working dir)
import os, shutil, numpy as np, trimesh

# out/ file -> (colour folder, file name, qty, settings / notes)
PARTS = [
    ("bottom",              "charcoal",  "case_bottom",        1, "0.2 mm layers; supports only for the front port openings. The NFC mark is engraved in its underside (prints on the bed)"),
    ("screen_back",         "charcoal",  "lid_shell",          1, "0.2 mm layers, back face down"),
    ("box_hatch",           "charcoal",  "hinge_box_hatch",    1, "0.2 mm layers"),
    ("keyboard_top",        "dark-grey", "keyboard_plate",     1, "**0.12 mm layers**: the webs between keys are 0.42 mm"),
    ("screen_front",        "dark-grey", "screen_bezel",       1, "0.12–0.16 mm layers, face down"),
    ("battery_door",        "yellow",    "battery_door",       1, "**print upright, with a brim** (0.4 mm skin)"),
    ("battery_lock_slider", "yellow",    "battery_lock_clip",  1, "0.12 mm layers"),
    ("hinge_cap",           "yellow",    "torque_hinge_cap",   1, "0.12 mm layers, logo up"),
    ("hinge_axle",          "yellow",    "hinge_axle",         1, "0.12 mm layers, flange down"),
    ("switch_knob",         "yellow",    "switch_knob",        1, "0.12 mm layers, flat back down, fin up; goes in from inside the case, the switch lever drops into its open-top socket"),
    ("battery_strip_test",  "tests",     "battery_door_fit_test", 1, "optional: the door, lock and chamber end, to check the fit first"),
]
COLOURS = {
    "charcoal":  ("Charcoal `#2D2D2D`", "Bambu PLA Matte Charcoal"),
    "dark-grey": ("Dark grey `#3D3D3D`", "Bambu PLA Basic Dark Gray"),
    "yellow":    ("Cyber yellow `#F7D116`", "Bambu PLA Basic Sunflower Yellow"),
    "tests":     ("any", "any scrap filament"),
}

def main():
    if os.path.isdir("print"):
        shutil.rmtree("print")
    rows = []
    for src, folder, name, qty, note in PARTS:
        m = trimesh.load(f"out/{src}.stl")
        lo, hi = m.bounds
        m.apply_translation((-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]))   # centred, on the bed
        os.makedirs(f"print/{folder}", exist_ok=True)
        m.export(f"print/{folder}/{name}.stl")
        size = hi - lo
        rows.append((folder, name, qty, size, note))
        print(f"print/{folder}/{name}.stl  {size[0]:.1f} x {size[1]:.1f} x {size[2]:.1f} mm")

    md = ["# Print files", "",
          "One folder per filament colour, so each folder is one print batch. Every part is already in its print orientation, flat on the bed.",
          "PLA, 0.4 mm nozzle. Rebuild this folder from the CAD with `python3 cad/export_print.py`.", ""]
    for folder in ("charcoal", "dark-grey", "yellow", "tests"):
        col, fil = COLOURS[folder]
        md += [f"## `{folder}/` · {col}" + (f" (e.g. {fil})" if folder != "tests" else ""), "",
               "| File | Qty | Size (mm) | Settings |", "|---|---|---|---|"]
        for f, name, qty, size, note in rows:
            if f == folder:
                md.append(f"| `{name}.stl` | {qty} | {size[0]:.1f} × {size[1]:.1f} × {size[2]:.1f} | {note} |")
        md.append("")
    md += ["## Also needed", "",
           "- 8 × M2 heat-set inserts (3.5 OD × 3 mm): 4 in the hinge-box floor, 4 in the lid shell",
           "- 12 × M2 × 4 countersunk screws",
           "- ~26 mm of 1.75 mm filament as the battery-door hinge pin",
           "- 1 × SS12D00 mini slide switch (SPDT, 8.6 × 3.6 × 3.5 mm body) for power: trim its lever to 1.05 mm",
           "",
           "**Optional paint fill.** The logos, MINIDECK text, side stripes and the NFC mark under the PN532 are engraved 0.3–0.6 mm deep. Go over them with a paint marker and wipe the surface with IPA.",
           "",
           "Full build steps: [../BUILD.md](../BUILD.md)"]
    open("print/README.md", "w").write("\n".join(md) + "\n")

if __name__ == "__main__":
    main()
