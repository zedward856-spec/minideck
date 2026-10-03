"""The user's part placement, taken straight from minideck.stl and moved into the case frame.

Nothing here is re-arranged except:
  * the battery, which slides ~11 mm left so the door spring reaches it (chamber in battery_test.py)
  * the DAC, 0.4 mm lower so its jack clears the upside-down Radxa above it
"""
import os
import numpy as np
import trimesh
from params import *

MINIDECK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "minideck.stl")
KEYBOARD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "keyboard.stl")   # the user's keyboard model
DAC_DROP = 0.4 + 1.22          # (+1.22: room for the real Radxa's underside chips)
# The official Radxa ZERO 3W model showed its microSD socket (2.9 mm) 0.72 mm into the keyboard and
# its underside chips into the DAC. Without making the deck thicker, the stack moves down instead:
RADXA_DROP = 0.82              # Radxa (and so its ports, pegs, the charger level with it)
LORA_DROP = 0.88               # LoRa, to stay under the lowered DAC
PN532_DROP = 0.4               # PN532 sits in a 0.4 mm pocket in the floor (floor 0.8 there)
MT3608_DROP = 0.5              # boost, to stay clear of the lowered charger
TP4056_SHIFT_X = 0.9           # charger 0.9 mm toward the Radxa: room for the power switch beside it (flush knob)
# ports right behind the front wall, so the wall can hug them (the user's request)
PORT_GAP = 0.1

# body index in minideck.stl (sorted by bounding-box volume) -> name
_BODIES = {1: "keyboard", 3: "battery", 4: "radxa", 5: "pn532", 7: "dac", 8: "mt3608",
           9: "tp4056", 10: "lora", 11: "lora"}


def placed_meshes():
    m = trimesh.load(MINIDECK)
    parts = sorted(m.split(only_watertight=False), key=lambda p: -p.bounding_box.volume)
    out = {}
    for i, name in _BODIES.items():
        p = parts[i].copy()
        p.apply_translation(MD_OFFSET)
        if name == "radxa":                      # headerless board: drop the 40-pin header pins
            keep = np.all((p.vertices[:, 2] > 14.5 + MD_OFFSET[2])[p.faces], axis=1)
            p.update_faces(keep)
            p.remove_unreferenced_vertices()
        if name == "dac":
            p.apply_translation((0, 0, -DAC_DROP))
        if name == "keyboard":                   # the user's keyboard model, at its placed spot,
            kb = trimesh.load(KEYBOARD)          # raised: the Radxa's microSD side faces up
            kb.apply_translation(p.bounds[0] - kb.bounds[0])
            if KB_TURN:                          # turn in place about its own centre
                c = (kb.bounds[0] + kb.bounds[1]) / 2
                kb.apply_transform(trimesh.transformations.rotation_matrix(np.radians(KB_TURN), [0, 0, 1], c))
            p = kb
            p.apply_translation((0, 0, RADXA_TOP_PARTS))
            if GROVE_REMOVED:                    # desoldered: drop the connector block off the model
                p = _cut_grove(p)
        out[name] = p if name not in out else trimesh.util.concatenate([out[name], p])
    # Radxa, charger and DAC slide forward until their ports touch the front wall
    for name in ("radxa", "tp4056", "dac"):
        m = out[name]
        front = m.bounds[0][1]
        m.apply_translation((0, FRONT_WALL + PORT_GAP - front, 0))
    out["radxa"].apply_translation((0, 0, -RADXA_DROP))
    out["lora"].apply_translation((0, 0, -LORA_DROP))
    out["pn532"].apply_translation((0, 0, -PN532_DROP))
    out["mt3608"].apply_translation((0, 0, -MT3608_DROP))
    # charger up so its USB-C sits level with the Radxa's two
    rz = out["radxa"].bounds[1][2] - 1.2 - 3.1 / 2
    tp = out["tp4056"].vertices
    usb = tp[tp[:, 1] < tp[:, 1].min() + 0.2]
    out["tp4056"].apply_translation((TP4056_SHIFT_X, 0, rz - (usb[:, 2].min() + usb[:, 2].max()) / 2))
    return out


def _cut_grove(kb):
    import manifold3d as mf
    s = kb.section(plane_origin=[0, 0, kb.bounds[0][2] + 4.0], plane_normal=[0, 0, 1])
    pp, _ = s.to_2D(to_2D=np.eye(4))
    g = max(pp.polygons_full, key=lambda q: q.area).bounds          # the tallest block = Grove
    top = kb.bounds[0][2] + 3.3                                      # keyboard body top
    k = kb.copy(); k.merge_vertices()
    km = mf.Manifold(mf.Mesh(vert_properties=np.asarray(k.vertices, np.float32),
                             tri_verts=np.asarray(k.faces, np.uint32)))
    cut = mf.Manifold.cube([g[2] - g[0] + 0.2, g[3] - g[1] + 0.2, 10]).translate([g[0] - 0.1, g[1] - 0.1, top])
    out = (km - cut).to_mesh()
    return trimesh.Trimesh(out.vert_properties[:, :3], out.tri_verts)


_M = None


def meshes():
    global _M
    if _M is None:
        _M = placed_meshes()
    return _M


def bounds(name):
    b = meshes()[name].bounds
    return tuple(float(v) for v in b[0]) + tuple(float(v) for v in b[1])


def radxa_ports():
    """Upside-down Radxa: USB-C, USB-C, micro-HDMI along its front edge (case x ranges)."""
    b = bounds("radxa")
    fx = lambda lx: b[3] - lx                    # its right end = the model's x = 0 end
    return {"usbc_a": (fx(58.5), fx(49.56)), "usbc_b": (fx(46.04), fx(37.1)),
            "hdmi": (fx(18.0), fx(9.0)), "face_y": b[1], "z": (b[5] - 1.2 - 3.1, b[5] - 1.2)}


def radxa_holes():
    b = bounds("radxa")
    y0 = b[4] - 30.0                             # board edge (30 mm deep board, ports overhang in front)
    return [(b[3] - lx, y0 + ly) for lx in (3.5, 61.5) for ly in (3.5, 26.5)]


def port_cutouts():
    tp = meshes()["tp4056"].vertices
    f = tp[tp[:, 1] < tp[:, 1].min() + 0.2]
    dac = meshes()["dac"].vertices
    j = dac[dac[:, 1] < dac[:, 1].min() + 0.05]
    return {"charger_usbc": (f[:, 0].min(), f[:, 0].max(), f[:, 2].min(), f[:, 2].max(), f[:, 1].min()),
            "jack": ((j[:, 0].min() + j[:, 0].max()) / 2, (j[:, 2].min() + j[:, 2].max()) / 2, j[:, 1].min())}


if __name__ == "__main__":
    for n in meshes():
        print(f"{n:9s}", [round(v, 2) for v in bounds(n)])
    rp = radxa_ports()
    print("radxa ports", {k: tuple(round(x, 2) for x in v) if isinstance(v, tuple) else round(v, 2) for k, v in rp.items()})
    print("radxa holes", [(round(x, 2), round(y, 2)) for x, y in radxa_holes()])
    print("ports", {k: [round(float(x), 2) for x in v] for k, v in port_cutouts().items()})
