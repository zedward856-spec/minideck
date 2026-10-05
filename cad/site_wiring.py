"""Data for the site's wiring page: the wiring plan (wiring.py) + Obsidian canvases -> ../minideck-site/wiring/.

    python3 cad/site_wiring.py      (after cad/wiring.py and cad/wiring_canvas.py)
"""
import _here  # noqa: F401  (repo root as the working dir)
import os, json, shutil

OUT = os.path.expanduser("~/minideck-site/wiring")

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    site = json.load(open("out/wiring_site.json"))
    data = dict(wires=json.load(open("out/wires.json")), **site)
    json.dump(data, open(f"{OUT}/data.json", "w"), indent=1)
    for f in ("minideck-wiring-all.canvas", "minideck-wiring-power.canvas"):
        shutil.copy2(f"wiring/{f}", f"{OUT}/{f}")
    print(f"wiring page data: {len(data['wires'])} wires, {len(data['pins'])} header pins, {len(data['notes'])} notes -> {OUT}")
