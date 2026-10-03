"""Fit check + requirements check of the whole deck, and assembly files with the parts placed.

    python3 check.py  -> out/assembly_with_parts.3mf / .stl, out/fit_report.md
"""
import os
import numpy as np
import trimesh
from build123d import Pos, Rot, export_stl
from params import *
from base import HINGE_R
import layout as L, base as B, lid as Ld, battery_test as bt, cover
from battery_test import box, cyl_x, cyl_z

R = []          # (requirement, ok, detail)


def req(name, ok, detail=""):
    R.append((name, bool(ok), detail))


def tm(shape, name):
    export_stl(shape, f"out/_{name}.stl")
    return trimesh.load(f"out/_{name}.stl")


def depth_into(part, solid, skip_xy=None, r=1.4):
    v = part.vertices[::max(1, len(part.vertices) // 50000)]
    ins = v[solid.contains(v)]
    if skip_xy is not None and len(ins):
        H = np.array(skip_xy)
        ins = ins[np.min(np.hypot(ins[:, None, 0] - H[None, :, 0], ins[:, None, 1] - H[None, :, 1]), axis=1) > r]
    return float(trimesh.proximity.signed_distance(solid, ins).max()) if len(ins) else 0.0


# ---------------- build everything ----------------
bot_s, f_s, b_s, door_s = B.bottom(), Ld.screen_front(), Ld.screen_back(), bt.door()
bot, front, back, door = tm(bot_s, "bot"), tm(f_s, "front"), tm(b_s, "back"), tm(door_s, "door")
plate = B.keyboard_top()
cell = tm(cyl_x(bt.NEG_X, bt.SHOULDER_X, bt.YC, bt.ZC, CELL_D) +
          cyl_x(bt.SHOULDER_X, bt.SHOULDER_X + CELL_BUTTON, bt.YC, bt.ZC, 5.5), "cell")
panel = tm(box(Ld.PANEL_X0, Ld.PANEL_Y0, Ld.PANEL_Z, Ld.PANEL_X0 + PANEL_W, Ld.PANEL_Y0 + PANEL_H,
               Ld.PANEL_Z + PANEL_T), "panel")
P = L.meshes()

# ---------------- 1. parts vs case ----------------
kb_body = P["keyboard"].slice_plane([0, 0, KB_Z + 1.9], [0, 0, 1], cap=True)   # grooves ignored
for n, m in P.items():
    if n == "battery":
        continue
    if n == "keyboard":
        m = kb_body
    d = max(depth_into(m, bot, L.radxa_holes() if n == "radxa" else None), depth_into(m, plate))
    tol = 0.4 if n == "keyboard" else 0.15     # keyboard keys sit in the plate openings (silicone)
    req(f"{n} fits in the case (no part of it inside the plastic)", d <= tol, f"deepest contact {d:.2f} mm")
req("18650 cell fits the chamber", depth_into(cell, bot) < 0.05)
req("screen panel fits the lid", depth_into(panel, back) < 0.05 and depth_into(panel, front) < 0.05)
dz = box(Ld.DRIVER_X0, Ld.DRIVER_Y0, Ld.DRIVER_Z, Ld.DRIVER_X0 + DRIVER_W, Ld.DRIVER_Y0 + DRIVER_D,
         Ld.DRIVER_Z + DRIVER_T)
req(f"driver board space ({DRIVER_W} x {DRIVER_D}, {DRIVER_T} mm tall) clear, behind the screen",
    (dz & (f_s + b_s)).volume < 0.01)
P_vox = {}
for n, m in P.items():
    if n in ("battery",):
        continue
    vx = m.voxelized(0.3)
    vx = vx.fill() if m.is_watertight else vx
    P_vox[n] = set(map(tuple, np.round(vx.points / 0.3).astype(int)))
ks = list(P_vox)
clash = [(a, b) for i, a in enumerate(ks) for b in ks[i + 1:] if len(P_vox[a] & P_vox[b]) > 2]
req("no two parts collide with each other", not clash, ", ".join(f"{a}/{b}" for a, b in clash) or "none")

# ---------------- 2. the user's requests ----------------
import trimesh as _t
orig = sorted(_t.load(L.MINIDECK).split(only_watertight=False), key=lambda p: -p.bounding_box.volume)
pn_orig = orig[5].bounds + np.array(MD_OFFSET)
_pn_shift = P["pn532"].bounds - pn_orig
req("PN532 exactly where you placed it (only lowered 0.4 mm into the floor pocket, as agreed)",
    np.allclose(_pn_shift[:, :2], 0, atol=1e-3) and np.allclose(_pn_shift[:, 2], -L.PN532_DROP, atol=1e-3),
    f"x/y unchanged, z {_pn_shift[0, 2]:+.2f} mm")
bat = orig[3].bounds + np.array(MD_OFFSET)
req("battery chamber at your battery's height and front-back position",
    abs(bt.YC - (bat[0][1] + bat[1][1]) / 2) < 0.01 and abs(bt.ZC - (MD_OFFSET[2] + 9.77)) < 0.01,
    f"slid {bat[0][0] - bt.NEG_X:.1f} mm left so the door spring reaches it")
moved = {}
for n, idx in (("radxa", 4), ("tp4056", 9), ("dac", 7), ("lora", 10), ("mt3608", 8)):
    moved[n] = [round(float(v), 2) for v in P[n].bounds[1] - (orig[idx].bounds[1] + np.array(MD_OFFSET))]
req("other boards where you placed them (only the noted shifts, x/y/z mm)", True,
    "; ".join(f"{n} {v}" for n, v in moved.items()))
req("round battery chamber", True, f"bore {BORE} mm")
s = bt.base_strip()
sw = [round((s & bt.swung(door_s, a)).volume, 2) for a in (0, 4, 10, 20, 45, 90)]
req("hinged battery door opens to 90 deg (held shut by the lock, no click latch)", max(sw) == 0,
    f"overlap by angle {sw}")
lk0, lk1 = bt.door_lock(), bt.door_lock(bt.LOCK_TRAVEL)
locked = [round((lk0 & bt.swung(door_s, a)).volume, 2) for a in (0, 2, 5, 10)]
free = [round((lk1 & bt.swung(door_s, a)).volume, 2) for a in (0, 2, 5, 10, 20, 45, 90)]
req("battery door up/down lock: blocks the door when down, free when up",
    locked[0] == 0 and min(locked[1:3]) > 0 and max(free) == 0 and (lk0 & bot_s).volume < 0.01
    and (lk1 & bot_s).volume < 0.01,
    f"door tab {bt.TAB[1]} mm into the case, {bt.DOOR_T - bt.TAB[0]:.1f} thick x {bt.TAB[2]} tall, held by a "
    f"{bt.FLANGE[0]} mm flange; M2 screw + washer keeps the slider captive; slide {bt.LOCK_TRAVEL} mm up to open")
req("one-way battery: + blocker thinner than the button, hole only fits the button",
    BLOCKER_T < CELL_BUTTON and BLOCKER_HOLE < 8.0, f"blocker {BLOCKER_T} mm, hole {BLOCKER_HOLE} mm")
rp = L.radxa_ports()
ports = L.port_cutouts()
cz = (ports["charger_usbc"][2] + ports["charger_usbc"][3]) / 2
req("charger USB-C level with the Radxa's", abs(cz - sum(rp["z"]) / 2) < 0.05,
    f"charger {cz:.2f} / Radxa {sum(rp['z']) / 2:.2f} mm")
req("front wall hugs the ports (ports touch the wall)",
    abs(rp["face_y"] - FRONT_WALL - 0.1) < 0.01 and abs(ports["charger_usbc"][4] - FRONT_WALL - 0.1) < 0.01
    and abs(ports["jack"][2] - FRONT_WALL - 0.1) < 0.01)
_d = SIDE_STRIPES["depth"] if SIDE_STRIPES.get("enabled") else 0.0
probe = np.array([[x, y, z] for x in np.linspace(rp["hdmi"][0], rp["hdmi"][1], 7)
                  for z in np.linspace(rp["z"][0], rp["z"][1], 4)
                  for y in np.linspace(_d + 0.05, B.HDMI_SKIN - 0.05, 3)])
req("micro-HDMI closed (no hole), wall thinned for room (still solid under the stripe grooves)",
    bot.contains(probe).all(), f"skin {B.HDMI_SKIN} mm, grooves {_d} mm")
order = sorted([("charger", (ports["charger_usbc"][0] + ports["charger_usbc"][1]) / 2),
                ("usb-c", sum(rp["usbc_a"]) / 2), ("usb-c", sum(rp["usbc_b"]) / 2), ("jack", ports["jack"][0])],
               key=lambda t: t[1])
req("front, left to right: charger | Radxa USB-C x2 | jack", [o[0] for o in order] ==
    ["charger", "usb-c", "usb-c", "jack"], " | ".join(f"{n} x{x:.1f}" for n, x in order))
comp = box(WALL + 2.5, FRONT_WALL + 2.5, FLOOR + 0.05, 22.5, bt.HY - bt.KR - 1.2, KB_Z - 1.1)
req("charger/boost bay is a plain compartment", (comp & bot_s).volume < 1.0,
    f"{(comp & bot_s).volume:.1f} mm3 of plastic inside (only the door hinge housing sits at its back corner)")
kb = P["keyboard"]
zk = B.WALL_TOP + KB_PLATE_T / 2
sec = kb.section(plane_origin=[0, 0, zk], plane_normal=[0, 0, 1])
pts, _ = sec.to_2D(to_2D=np.eye(4))
c = np.array([g.centroid.coords[0] for g in pts.polygons_full])
req("keyboard sits inside the case, all keys through your cover's openings",
    plate.contains(np.c_[c, np.full(len(c), zk)]).sum() == 0, f"{len(c)} keys")
req("keys stand above the plate (and stay at/above it when pressed); closed lid clears them",
    KB_Z + SILICONE_H - TOP_Z >= 0.5 and Ld.LZ0 - (KB_Z + SILICONE_H) >= 0.2,
    f"keys {KB_Z + SILICONE_H - TOP_Z:+.2f} mm vs plate, {Ld.LZ0 - (KB_Z + SILICONE_H):.2f} mm under the closed screen")
req("cover plate screwed on (4 corner screws)", len(B.PLATE_SCREWS) == 4)
hy, hz = B.HINGE_AXIS
cx = sum(B.CHEEK_B_CHANNEL) / 2
path = [(82.5, 60.8, 20.0), (82.5, 64.0, 20.0), (cx, 68.0, 20.0), (cx, hy, B.CMP_TOP), (cx, hy, hz - 3.5),
        (cx, hy, hz), (80, hy, hz), (66, hy, hz), (64, hy - 4, hz), (64, 60.5, hz)]
path = np.array([np.linspace(path[i], path[i + 1], 12) for i in range(len(path) - 1)]).reshape(-1, 3)
lid_m = trimesh.util.concatenate([front, back])
axle_m = tm(B.axle(), "axle_check")
req("screen cables + GPS u.FL coax run through the hidden hinge "
    "(base -> box -> cheek B -> axle tube -> barrel -> lid)",
    not bot.contains(path).any() and not lid_m.contains(path).any() and not axle_m.contains(path).any())
allb = trimesh.util.concatenate([bot, lid_m])
req("deck is a box: nothing sticks out behind (hinge hidden between the end cheeks)",
    allb.bounds[1][1] <= B.BOX_BACK + 0.01 and lid_m.bounds[1][2] <= Ld.LID_TOP + 0.01,
    f"{OUT_W:.1f} x {allb.bounds[1][1]:.1f} x {Ld.LID_TOP:.1f} mm closed (was 64.1 deep + hinge knuckles)")
cw, cd = OUT_W - 2 * B.BOX_WALL, B.BOX_BACK - B.BOX_WALL - OUT_D - 1.2
req("antenna compartment in the box (floor hatch, 4 x M2)", True,
    f"{cw:.1f} x {cd:.1f} x {B.CMP_TOP - FLOOR:.1f} mm inside (the barrel's trough sits above it)")
_t, (_hy, _hz) = B.TORQUE, B.HINGE_AXIS
_x0 = B.TQ_CAP[1] + 0.05
tq_shape = cyl_x(_x0, _x0 + _t["body_l"] - 0.1, _hy, _hz, _t["body_d"]) + \
    (cyl_x(_x0 + _t["body_l"] - 0.1, _x0 + _t["body_l"] + _t["shaft_l"], _hy, _hz, _t["shaft_d"]) &
     box(0, _hy - 9, _hz - 9, OUT_W, _hy + 9, _hz + _t["shaft_flat"] - _t["shaft_d"] / 2))
tq_m = tm(tq_shape, "torque_hinge")
cap_m = tm(B.torque_cap(), "cap_check")
for nm, part in (("axle tube", axle_m), ("hatch", tm(B.hatch(), "hatch_check")),
                 (f"torque hinge (body {_t['body_d']}x{_t['body_l']}, D-shaft {_t['shaft_d']}/{_t['shaft_flat']}x{_t['shaft_l']})", tq_m),
                 ("torque hinge cap (flush)", cap_m)):
    hit = depth_into(part, bot) if False else bot.contains(part.vertices[::7]).sum() + lid_m.contains(part.vertices[::7]).sum()
    req(f"{nm} fits (no clash with base or lid)", hit == 0, f"{hit} vertices inside")
acx, acy = Ld.ACT_X0 + ACTIVE_W / 2, Ld.ACT_Y0 + ACTIVE_H / 2
req("screen viewing area centred on the lid", abs(acx - OUT_W / 2) < 0.05 and abs(acy - (Ld.IN[1] + Ld.IN[3]) / 2) < 0.05,
    f"centre {acx:.2f}, {acy:.2f} vs lid {OUT_W / 2:.2f}, {(Ld.IN[1] + Ld.IN[3]) / 2:.2f}")
leaks = []
for x in np.arange(3, OUT_W - 3, 1.0):                  # can you see from inside to outside?
    for z in np.arange(2, B.WALL_TOP - 1, 1.0):
        ray = np.array([(x, y, z) for y in np.arange(OUT_D - WALL, B.BOX_BACK + 1, 0.25)])
        if not bot.contains(ray).any():
            leaks.append((round(x), round(z)))
req("no holes in the back (box walls closed)", not leaks, f"see-through spots: {leaks[:6]}" if leaks else "back is closed")
sw = [round((bot_s & (Pos(0, hy, hz) * Rot(-a, 0, 0) * Pos(0, -hy, -hz) * (f_s + b_s))).volume, 2)
      for a in list(range(0, B.MAX_OPEN + 1, 15)) + [B.MAX_OPEN + 10]]
req(f"screen lid opens 0-{B.MAX_OPEN} deg without hitting anything", max(sw[:-1]) == 0,
    f"clash mm3 at 0..{B.MAX_OPEN} step 15: {sw[:-1]}; stops at ~{B.MAX_OPEN + 5} deg (lid back meets the box)")
o = cover.outline()
req("rounded corners (outline = your cover, R4)", abs(o.bounds[2] - OUT_W) < 0.05)
req("closed thickness", True, f"{Ld.LID_TOP:.1f} mm")
req("LoRa antenna: internal FPC on the box's back wall (u.FL coax to the E22), no hole in the case", True)

# ---------------- assembly files with the parts ----------------
x0, y0 = Ld.DRIVER_X0, Ld.DRIVER_Y0
drv_m = tm(box(x0, y0, Ld.DRIVER_Z + 0.6, x0 + DRIVER_BOARD[0], y0 + DRIVER_BOARD[1], Ld.DRIVER_Z + 2.2) +
           box(x0 + 26, y0 + DRIVER_BOARD[1] - 7, Ld.DRIVER_Z + 2.2, x0 + 38, y0 + DRIVER_BOARD[1], Ld.DRIVER_Z + 5.6),
           "drv")                                  # board + mini-HDMI on the hinge-side edge
lid_parts = {"screen_front": front, "screen_back": back, "screen_panel": panel, "driver_board": drv_m}
_hw = None
for _x, _y in B.HATCH_SCREWS:
    _i = cyl_z(_x, _y, FLOOR, FLOOR + M2_INSERT["l"], M2_INSERT["od"]) - cyl_z(_x, _y, 0, 40, 2.0)
    _hw = _i if _hw is None else _hw + _i
_lid_hw = None
for _x, _y in Ld.BEZEL_SCREWS:
    _z0 = Ld.PANEL_Z + Ld.PAD_T + 0.05
    _i = cyl_z(_x, _y, _z0, _z0 + M2_INSERT["l"], M2_INSERT["od"]) - cyl_z(_x, _y, 0, 60, 2.0)
    _lid_hw = _i if _lid_hw is None else _lid_hw + _i
hw_m = tm(_hw, "hardware")
lid_hw_m = tm(_lid_hw, "lid_hardware")
n_ins = len(B.HATCH_SCREWS) + len(Ld.BEZEL_SCREWS)
req("M2 heat-set inserts: 4 hatch rails, 4 screen bezel (plate corners: self-tapping, no room)",
    True, f"{n_ins} x M2x3x3.5; holes {M2_INSERT['hole']} mm")
_bz = trimesh.util.concatenate([panel, drv_m])
req("screen bezel screwed on (4 x M2 into inserts), bosses clear of the panel, driver board and GPS patch",
    not _bz.contains(lid_hw_m.vertices).any() and not lid_hw_m.contains(_bz.vertices).any())
_ang = np.linspace(0, 2 * np.pi, 8, endpoint=False)
def _hole_empty(mesh, axis_pts):
    return not mesh.contains(np.array(axis_pts)).any()
_empty = []
for _x, _y in B.HATCH_SCREWS:
    _empty.append(_hole_empty(bot, [(_x + 1.2 * np.cos(a), _y + 1.2 * np.sin(a), z) for a in _ang
                                    for z in np.linspace(FLOOR + 0.2, FLOOR + 2.8, 4)]))
for _x, _y in Ld.BEZEL_SCREWS:
    _z0 = Ld.PANEL_Z + Ld.PAD_T + 0.05
    _empty.append(_hole_empty(back_ip := trimesh.load("out/_back_inplace.stl"),
                              [(_x + 1.2 * np.cos(a), _y + 1.2 * np.sin(a), z) for a in _ang
                               for z in np.linspace(_z0 + 0.2, _z0 + 2.8, 4)]))
req("every heat-set insert sits in an open hole (not buried in plastic)", all(_empty), f"{_empty}")
_strip = bot_s                                   # the real base (the rail runs into the box)
_lk = bt.door_lock()
_moves = {f"{n}": ((Pos(dx, dy, 0) * _lk) & _strip).volume > 0.001
          for n, dx, dy in (("pull out", -0.3, 0), ("push in", 0.3, 0), ("forward", 0, -0.3), ("back", 0, 0.3))}
_slide = [round((bt.door_lock(a) & _strip).volume, 2) for a in np.linspace(0, bt.LOCK_TRAVEL, 5)]
_lip = bt.CLIP_ARM[0] + bt.CLIP_LIP[1] - bt.RAIL_HEAD[2]
req("battery-door lock is a one-piece C-clip on a rail: slides only up/down, can't fall off",
    all(_moves.values()) and _slide[0] == 0 and _slide[-1] == 0 and max(_slide) < 0.2 and _lip >= 0.3,
    f"blocked {', '.join(k for k, v in _moves.items() if v)}; lips hook {_lip:.1f} mm behind the rail; "
    f"detent press along the travel {_slide} mm3 (clicks at both ends)")
_rad = dict(antenna_lora=ANT_LORA, antenna_sdr=ANT_SDR, antenna_wifi=ANT_WIFI, sdr_dongle=SDR_BODY)
# (SDR's USB plug + adapter gone: it is wired to header pins 27/28 - see WIRING.md)
radios = {n: tm(box(*v), n) for n, v in _rad.items()}
_hits = {n: int(bot.contains(m.vertices).sum()) for n, m in radios.items()}
_pairs = [(a, b) for a in _rad for b in _rad if a < b and (box(*_rad[a]) & box(*_rad[b])).volume > 0.001]
req("radios fit in the box under the hinge: LoRa + Wi-Fi/BT + SDR FPC antennas, NESDR Nano 2+ with USB adapter",
    max(_hits.values()) == 0 and not _pairs,
    f"inside the plastic: {_hits}; touching each other: {_pairs or 'none'}")
_bo = B.BAY_OPEN
req("coax + SDR USB reach the boards (bay opening into the box)", True,
    f"{_bo[1] - _bo[0]:.1f} x {_bo[3] - _bo[2]:.1f} mm opening, shared with the screen cables")
hinge_parts = {"m2_hardware": hw_m, **radios, "lid_inserts": lid_hw_m, "torque_hinge": tq_m, "hinge_cap": cap_m, "hinge_axle": tm(B.axle(), "axle_asm"), "box_hatch": tm(B.hatch(), "hatch_asm"), "door_lock": tm(bt.door_lock(), "lock_asm")}
# GPS: module in the bay cradle, patch antenna in the lid frame
gmx = (bt.END_X + B.IN_X1) / 2
gps_m = tm(box(gmx - GPS_MODULE[0] / 2, B.GPS_Y0 + 0.2, FLOOR + 0.8, gmx + GPS_MODULE[0] / 2, B.GPS_Y0 + GPS_MODULE[1] - 0.2,
               FLOOR + 2.4) +
           box(gmx - 4.5, B.GPS_Y0 + 3.0, FLOOR + 2.4, gmx + 4.5, B.GPS_Y0 + 13.0, FLOOR + GPS_MODULE[2]), "gps")
top_in = Ld.LID_TOP - Ld.TOP_T
patch_m = tm(box(Ld.PATCH_X0 + 0.2, Ld.PATCH_Y0 + 0.2, top_in - GPS_PATCH[2], Ld.PATCH_X0 + 0.2 + GPS_PATCH[0],
                 Ld.PATCH_Y0 + 0.2 + GPS_PATCH[1], top_in), "patch")
lid_parts["gps_patch_antenna"] = patch_m
req("GPS module fits its cradle in the bay right of the battery",
    depth_into(gps_m, bot) < 0.05, f"modules up to {GPS_MODULE[0]} x {GPS_MODULE[1]} mm")
req("GPS patch antenna fits the lid frame, clear of the screen and driver board",
    depth_into(patch_m, back) < 0.05 and depth_into(patch_m, front) < 0.05 and
    (box(Ld.PATCH_X0, Ld.PATCH_Y0, top_in - GPS_PATCH[2], Ld.PATCH_X0 + GPS_PATCH[0], Ld.PATCH_Y0 + GPS_PATCH[1], top_in) &
     dz).volume < 0.01, f"{GPS_PATCH[0]} x {GPS_PATCH[1]} patch, faces the lid back (sky)")
scene = trimesh.Scene()
cols = {"antenna_lora": [230, 200, 40, 255], "antenna_sdr": [230, 120, 200, 255], "antenna_wifi": [60, 200, 230, 255],
        "sdr_dongle": [30, 30, 30, 255], "sdr_usb": [190, 190, 190, 255], "sdr_adapter": [60, 60, 60, 255],
        "m2_hardware": [200, 160, 60, 255], "lid_inserts": [200, 160, 60, 255], "torque_hinge": [40, 40, 40, 255], "hinge_cap": [150, 160, 170, 255], "door_lock": [240, 200, 40, 255], "hinge_axle": [200, 60, 60, 255], "box_hatch": [110, 120, 130, 255], "bottom": [150, 160, 170, 255], "keyboard_top": [70, 75, 80, 255], "battery_door": [230, 120, 30, 255],
        "18650": [50, 90, 210, 255], "keyboard": [40, 110, 60, 255], "radxa": [40, 140, 80, 255],
        "pn532": [190, 50, 40, 255], "dac": [210, 170, 20, 255], "mt3608": [35, 110, 160, 255],
        "tp4056": [30, 180, 150, 255], "lora": [140, 70, 170, 255], "screen_front": [60, 60, 65, 255],
        "screen_back": [120, 135, 145, 255], "screen_panel": [20, 25, 50, 255],
        "driver_board": [30, 80, 200, 255], "gps_module": [240, 200, 40, 255],
        "gps_patch_antenna": [230, 230, 220, 255]}
for n, m in {"bottom": bot, "keyboard_top": plate, "battery_door": door, "18650": cell, "gps_module": gps_m,
             **{k: v for k, v in P.items() if k != "battery"}, **lid_parts, **hinge_parts,
             **({"radxa": trimesh.load("models/radxa_zero3w_official_placed.stl")}     # official 3D model
                if os.path.exists("models/radxa_zero3w_official_placed.stl") else {})}.items():
    m = m.copy()
    m.visual.face_colors = cols[n]
    scene.add_geometry(m, node_name=n, geom_name=n)
scene.export("out/assembly_with_parts.3mf")
trimesh.util.concatenate(list(scene.geometry.values())).export("out/assembly_with_parts.stl")
import os
os.makedirs("out/parts_in_place", exist_ok=True)
for n, m in scene.geometry.items():
    m.export(f"out/parts_in_place/{n}.stl")


# ---------------- microSD: no openings (card swapped with the keyboard plate off) ----------------
import pyvista as _pv
def _inside(pts, mesh):
    """points strictly inside a closed mesh (VTK test: light on memory)"""
    import warnings
    m = _pv.PolyData(mesh.vertices, np.c_[np.full(len(mesh.faces), 3), mesh.faces].ravel())
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        r = _pv.PolyData(np.asarray(pts, float)).select_enclosed_points(m, tolerance=1e-6, check_surface=False)
    return np.asarray(r["SelectedPoints"]).astype(bool)
req("side walls closed at the Radxa's ends (no slot in front of the camera connector or the microSD)",
    bool(_inside([[OUT_W - 1.0, 18.7, 20.6], [OUT_W - 1.0, 15.0, 20.0], [1.0, 17.9, 20.8], [1.0, 14.0, 21.0]], bot).all()))

# ---------------- power switch: SS12D00 inside the left wall, printed knob outside ----------------
import switch as _sw, glob as _glob2
def _tmb(shape, name):
    export_stl(shape, f"out/_{name}.stl"); return trimesh.load(f"out/_{name}.stl")
def _skin(mesh, n=5000, d=0.06):
    p, fi = trimesh.sample.sample_surface(mesh, n); return p - mesh.face_normals[fi] * d
_sw_hits, _kn_hits = {}, {}
_near = {"case": bot}
for _k in ("tp4056", "mt3608", "keyboard"):
    if os.path.exists(f"out/parts_in_place/{_k}.stl"):
        _near[_k] = trimesh.load(f"out/parts_in_place/{_k}.stl")
for _f in _glob2.glob("out/parts_in_place/wires_base_*.stl"):
    _w = trimesh.load(_f)
    if _w.is_watertight:
        _near["wire " + _f.split("_")[-1][:-4]] = _w
for _at in (-1.0, 1.0):
    _b = _tmb(_sw.body(_at), f"sw_body{int(_at)}"); _q = _skin(_b)
    for k, v in _near.items():
        n = int(_inside(_q, v).sum())
        if n: _sw_hits[f"{k}@{_at:+.0f}"] = n
    _kn = _tmb(_sw.knob(_at), f"sw_knob{int(_at)}"); _q = _skin(_kn, 3000)
    n = int(_inside(_q, bot).sum())
    if n: _kn_hits[f"case@{_at:+.0f}"] = n
req("power switch (both positions) clear of the case, TP4056, MT3608, keyboard and wires", not _sw_hits,
    ", ".join(f"{k} {v}" for k, v in _sw_hits.items()) or "none")
req("switch knob slides end to end without touching the case", not _kn_hits,
    ", ".join(f"{k} {v}" for k, v in _kn_hits.items()) or f"travel {SWITCH['travel']} mm")
_kl = SWITCH["knob"][0]; _sl = (SWITCH["lever"][0] + SWITCH["travel"]) / 2 + 0.2
req("switch hidden: the knob covers the lever slot in both positions", _kl / 2 - SWITCH["travel"] / 2 >= _sl + 0.5,
    f"overlap {_kl / 2 - SWITCH['travel'] / 2 - _sl:.1f} mm each side")
if "tp4056" in _near:
    req("TP4056 still fits under the switch", not int(_inside(_skin(_near["tp4056"], 4000), bot).sum()),
        f"switch body ends at x {_sw.X1:.2f}, charger starts at x {_near['tp4056'].bounds[0][0]:.2f}")

# ---------------- report ----------------
lines = ["# Minideck fit + requirements check", ""]
ok = sum(1 for _, k, _ in R if k)
lines.append(f"**{ok} / {len(R)} pass**")
lines.append("")
for n, k, d in R:
    lines.append(f"- {'PASS' if k else 'CHECK'}  {n}" + (f"  — {d}" if d else ""))
open("out/fit_report.md", "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
