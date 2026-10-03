"""Export the assembled deck for the promo website (three.js):
   ../minideck-site/assets/minideck.glb   - one node per part, lid parts under a 'lid' pivot on the hinge axis
   ../minideck-site/assets/parts.json     - per part: label, colour role, explode offset, group
Meshes are decimated for the web; the paint fills are merged into the part they sit in."""
import json, os, numpy as np, pyvista as pv, trimesh
from PIL import Image
import base as B, lid as Ld, keycaps
from params import ACTIVE_W, ACTIVE_H

SRC, OUT = "out/parts_in_place", os.path.expanduser("~/minideck-site/assets")
HY, HZ = B.HINGE_AXIS
LID = {"screen_front", "screen_back", "screen_panel", "driver_board", "gps_patch_antenna", "lid_inserts", "screws_lid",
       "fill_logos_lid", "fill_stripes_lid"}
# name: (label, role, max faces, explode offset in the part's own (closed) frame)
P = {
    "bottom":        ("Case bottom", "body", 60000, (0, 0, -32)),
    "box_hatch":     ("Hinge-box hatch", "body", 6000, (0, 18, -58)),
    "keyboard_top":  ("Keyboard plate", "kbplate", 30000, (0, 0, 44)),
    "battery_door":  ("Battery door", "accent", 8000, (-48, 0, 4)),
    "door_lock":     ("C-clip lock", "accent2", 3000, (-72, 0, 10)),
    "hinge_cap":     ("Torque hinge cap", "accent2", 6000, (-46, 6, 6)),
    "hinge_axle":    ("Hollow hinge axle", "accent2", 8000, (52, 6, 6)),
    "torque_hinge":  ("Torque hinge", "metal", 4000, (-28, 6, 6)),
    "keyboard":      ("M5Stack CardKB", "dark", 12000, (0, 0, 26)),
    "radxa":         ("Radxa ZERO 3W", "pcb_green", 0, (0, 0, 14)),
    "18650":         ("18650 cell", "cell", 4000, (-26, -8, 8)),
    "pn532":         ("PN532 NFC", "pcb_red", 6000, (14, -14, 10)),
    "dac":           ("PCM5102 DAC", "pcb_purple", 6000, (10, -22, 6)),
    "mt3608":        ("MT3608 boost", "pcb_blue", 4000, (18, 0, 10)),
    "tp4056":        ("TP4056 charger", "pcb_blue", 4000, (-6, -24, 6)),
    "lora":          ("E22 LoRa radio", "metal", 6000, (24, 10, 16)),
    "gps_module":    ("GPS module", "pcb_green", 4000, (22, -6, 18)),
    "sdr_dongle":    ("NESDR Nano 2+", "dark", 6000, (8, 20, -20)),
    "antenna_lora":  ("LoRa antenna", "flex", 1000, (0, 34, -6)),
    "antenna_wifi":  ("Wi-Fi/BT antenna", "flex", 1000, (0, 40, -10)),
    "antenna_sdr":   ("SDR antenna", "flex", 1000, (0, 46, -14)),
    "m2_hardware":   ("M2 inserts", "brass", 3000, (0, 10, -40)),
    "screws_base":   ("M2 screws", "metal", 6000, None),
    "screen_back":   ("Lid shell", "body", 50000, (0, 0, 34)),
    "screen_front":  ("Screen bezel", "kbplate", 20000, (0, 0, -26)),
    "screen_panel":  ("2.8\" IPS panel", "glass", 2000, (0, 0, -12)),
    "driver_board":  ("EHD-40P-V3 HDMI driver", "pcb_blue", 8000, (0, 0, 18)),
    "gps_patch_antenna": ("GPS patch antenna", "ceramic", 2000, (0, 0, 26)),
    "lid_inserts":   ("Lid M2 inserts", "brass", 2000, (0, 0, 8)),
    "screws_lid":    ("Bezel screws", "metal", 3000, (0, 0, -48)),
}
FILL_HOST = {"fill_logos_base": ["keyboard_top"], "fill_caps_base": ["hinge_cap", "hinge_axle"],
             "fill_stripes_base": ["bottom"], "fill_logos_lid": ["screen_back", "screen_front"],
             "fill_stripes_lid": ["screen_back"]}
FILL_ROLE = {"fill_caps_base": "fill_dark"}

def load(f, faces):
    m = pv.read(f"{SRC}/{f}.stl").triangulate().clean()
    if faces and m.n_cells > faces:
        m = m.decimate_pro(1 - faces / m.n_cells, preserve_topology=True, feature_angle=30, splitting=False)
    tm = trimesh.Trimesh(m.points, m.faces.reshape(-1, 4)[:, 1:], process=True)
    return tm

def radxa_box():
    """a plain green board in the Radxa's place (their model stays out of the public site), plus its
    silver USB-C / micro-HDMI shells (picked off the real mesh as in the viewer)."""
    import layout as L
    m = pv.read(f"{SRC}/radxa.stl").triangulate()
    b = m.bounds
    rp = L.radxa_ports(); lb = L.bounds("radxa")
    zp = (rp["z"][0] + rp["z"][1]) / 2 + 3.16 / 2
    board = trimesh.creation.box(bounds=[[b[0], b[2], zp - 0.08], [b[1], b[3], zp + 1.68]])
    c = m.cell_centers().points
    sel = (c[:, 2] < zp - 0.08) & (c[:, 1] < lb[1] + 7.5)
    shells = m.extract_cells(np.where(sel)[0]).extract_surface().triangulate()
    return board, trimesh.Trimesh(shells.points, shells.faces.reshape(-1, 4)[:, 1:])

def port_split(f, tm):
    """the charger's USB-C (silver) and the DAC's 3.5 mm jack (black) as their own pieces"""
    import layout as L
    pc = L.port_cutouts(); c = tm.triangles_center
    if f == "tp4056":
        x0, x1, z0, z1, yf = pc["charger_usbc"]
        sel = (c[:, 0] > x0 - .3) & (c[:, 0] < x1 + .3) & (c[:, 2] > z0 - .3) & (c[:, 2] < z1 + .3) & (c[:, 1] < yf + 7.6)
    else:
        jx, jz, yf = pc["jack"]
        sel = (np.hypot(c[:, 0] - jx, c[:, 2] - jz) < 3.4) & (c[:, 1] < yf + 13.0)
    return tm.submesh([np.where(~sel)[0]], append=True), tm.submesh([np.where(sel)[0]], append=True)

scene = trimesh.Scene()
lid_frame = np.eye(4); lid_frame[:3, 3] = (0, HY, HZ)
scene.graph.update(frame_to="lid", frame_from="world", matrix=lid_frame, geometry=None)
meta, meshes = {}, {}
for f, (label, role, faces, off) in P.items():
    if not os.path.exists(f"{SRC}/{f}.stl"):
        continue
    meshes[f] = load(f, faces) if f != "radxa" else None
extra = []                                          # (name, mesh, role, host)
board, shells = radxa_box(); meshes["radxa"] = board; extra.append(("radxa_ports", shells, "metal", "radxa"))
for f, role in (("tp4056", "metal"), ("dac", "dark")):
    meshes[f], port = port_split(f, meshes[f]); extra.append((f + "_port", port, role, f))

def add(name, tm, role, parent):
    tm = tm.copy()
    if parent == "lid":
        tm.apply_translation((0, -HY, -HZ))
    tm.metadata["name"] = name
    scene.add_geometry(tm, geom_name=name, node_name=name, parent_node_name=parent)

# screws: split into single screws, each flies off its own way
for f in ("screws_base", "screws_lid"):
    if f not in meshes:
        continue
    for i, s in enumerate(meshes.pop(f).split(only_watertight=False)):
        c = s.bounds.mean(0)
        up = c[2] > 14 if f == "screws_base" else False
        off = (0, 0, 70 if up else -60) if f == "screws_base" else (0, 0, -48)
        n = f"{f}_{i}"
        add(n, s, "metal", "lid" if f in LID else "world")
        meta[n] = dict(label=P[f][0], role="metal", explode=off, lid=f in LID, list=False)

# fills: each island goes with the nearest host part
for fill, hosts in FILL_HOST.items():
    if not os.path.exists(f"{SRC}/{fill}.stl"):
        continue
    parts = {h: [] for h in hosts}
    for comp in load(fill, 0).split(only_watertight=False):
        c = comp.bounds.mean(0)
        best = min(hosts, key=lambda h: abs(meshes[h].nearest.signed_distance([c])[0]) if len(hosts) > 1 else 0)
        parts[best].append(comp)
    for h, comps in parts.items():
        if comps:
            n = f"{fill}__{h}"
            add(n, trimesh.util.concatenate(comps), FILL_ROLE.get(fill, "accent"), "lid" if h in LID else "world")
            meta[n] = dict(label="paint fill", role=FILL_ROLE.get(fill, "accent"), host=h, lid=h in LID, list=False,
                           stripes="stripes" in fill)

for n, tm, role, host in extra:
    add(n, tm, role, "world")
    meta[n] = dict(label="", role=role, host=host, lid=False, list=False)

for f, tm in meshes.items():
    label, role, faces, off = P[f]
    add(f, tm, role, "lid" if f in LID else "world")
    c = tm.bounds.mean(0)
    meta[f] = dict(label=label, role=role, explode=off, lid=f in LID, list=True,
                   centre=[float(v) for v in c])

# keycaps (silicone bodies) + one legend texture covering the whole keyboard
caps = keycaps.build()[0]
bodies = [trimesh.Trimesh(b.triangulate().points, b.triangulate().faces.reshape(-1, 4)[:, 1:]) for b, s in caps if s is None]
add("keycaps", trimesh.util.concatenate(bodies), "keys", "world")
meta["keycaps"] = dict(label="Silicone keycaps", role="keys", explode=(0, 0, 66), lid=False, list=True)
planes = [(pl, s) for pl, s in caps if s is not None]
x0 = min(pl.bounds[0] for pl, _ in planes); x1 = max(pl.bounds[1] for pl, _ in planes)
y0 = min(pl.bounds[2] for pl, _ in planes); y1 = max(pl.bounds[3] for pl, _ in planes)
PX = 24
atlas = Image.new("RGBA", (int((x1 - x0) * PX), int((y1 - y0) * PX)), (0, 0, 0, 0))
for pl, (main, sec, w, h) in planes:
    im = keycaps.legend_image(main, sec, w, h, px=PX, key="#161616", ink="#f0f0f0").convert("RGBA")
    atlas.paste(im, (int((pl.bounds[0] - x0) * PX), int((y1 - pl.bounds[3]) * PX)))
atlas.save(f"{OUT}/legends.png")
z = planes[0][0].bounds[4]
meta["legends"] = dict(rect=[x0, y0, x1, y1], z=z, explode=(0, 0, 66), lid=False, list=False)

# the screen's active area (video goes here), in the lid frame
meta["_screen"] = dict(cx=Ld.ACT_X0 + ACTIVE_W / 2, cy=Ld.ACT_Y0 + ACTIVE_H / 2 - HY, z=Ld.PANEL_Z - 0.06 - HZ,
                       w=ACTIVE_W, h=ACTIVE_H, explode=(0, 0, -12))
meta["_hinge"] = dict(y=HY, z=HZ, max_open=B.MAX_OPEN)
scene.export(f"{OUT}/minideck.glb")
json.dump(meta, open(f"{OUT}/parts.json", "w"), indent=1, default=float)
print("glb", os.path.getsize(f"{OUT}/minideck.glb") // 1024, "kB,", len(meta), "entries")
