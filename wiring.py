"""Wiring plan + 3D wires for the assembly view.

    python3 wiring.py  -> out/parts_in_place/wires_*.stl (base and lid groups), WIRING.md

Wires are display models (tubes along the planned routes); the plan table is the real deliverable.
Routes use the free channels in the case:
  over the Radxa (header row, z ~20.8)   behind the Radxa (y ~35.2, in front of the battery block)
  down the right side (x ~90.3, above the GPS module)   the bay -> box passage -> cheek B -> hollow
  axle -> hinge barrel bore -> lid channel (x 60-68) -> lid interior above the bezel.
"""
import numpy as np, pyvista as pv, trimesh
from params import *
import layout as L, base as B, battery_test as bt, lid as Ld

# ---------------------------------------------------------------- Radxa header pads (case frame)
_b = L.bounds("radxa"); _rp = L.radxa_ports()
_ZP = (_rp["z"][0] + _rp["z"][1]) / 2 + 3.16 / 2         # same placement as the official model
PAD_Z = _ZP + 1.6                                          # the PCB face that now points up
def pad(n):
    """Radxa ZERO 3W header pin n. Pi-Zero layout assumed: pin 1 at the microSD end, odd pins on
    the inner row (model y 25.41), even pins on the edge row (27.95), 2.54 pitch."""
    col, even = (n - 1) // 2, n % 2 == 0
    mx, my = 8.32 + 2.54 * col, 27.95 if even else 25.41
    return np.array([_b[3] - mx, my + 1.5 + _b[1], PAD_Z])

def grove_pads():
    """Where the CardKB's (desoldered) Grove connector was: its through-hole pads, bottom side."""
    m = trimesh.load(L.MINIDECK)
    parts = sorted(m.split(only_watertight=False), key=lambda p: -p.bounding_box.volume)
    p = parts[1].copy(); p.apply_translation(MD_OFFSET)
    kb = trimesh.load(L.KEYBOARD); kb.apply_translation(p.bounds[0] - kb.bounds[0])
    c = (kb.bounds[0] + kb.bounds[1]) / 2
    kb.apply_transform(trimesh.transformations.rotation_matrix(np.radians(KB_TURN), [0, 0, 1], c))
    kb.apply_translation((0, 0, RADXA_TOP_PARTS))
    s = kb.section(plane_origin=[0, 0, kb.bounds[0][2] + 4.0], plane_normal=[0, 0, 1])
    pp, _ = s.to_2D(to_2D=np.eye(4))
    g = max(pp.polygons_full, key=lambda q: q.area).bounds
    return np.array([(g[0] + g[2]) / 2, (g[1] + g[3]) / 2, B.KB_Z])

GP = grove_pads()
hy, hz = B.HINGE_AXIS
YB, XR, ZT = 34.6, 90.3, 21.4          # behind-Radxa channel y, right-side channel x, over-Radxa z
GROOVE = (GP[0] - 2.0, bt.TUN_Y0 - DIVIDER - 0.3, GP[0] + 2.0, GP[1] + 3.0, 1.2)   # strip-top wire groove

# ---------------------------------------------------------------------------- routing helpers
# every wire gets its own lane in the shared channels, so no two wires share a path, and every
# Radxa header pad carries exactly ONE wire (chains and splices happen away from the board)
YB = 34.8                                  # behind-the-Radxa channel (Radxa ends 33.2, battery block 37.5)
HOP_EVEN, HOP_ODD = 21.1, 22.0            # height of the short hop onto the edge / inner pad row
_lane = [0]
def lane():
    """(channel y, channel z, right-side x) - 1.0 mm apart in y/z and 1.25 mm in x, so even the
    24 AWG / coax wires sit side by side instead of through each other."""
    k = _lane[0]; _lane[0] += 1
    return 33.95 + (k % 3) * 1.3, 7.9 + (k // 3) * 1.15, 90.6 - (k % 7) * 1.25

def header(pin, pre, ln):
    """pre: module-side points (ending somewhere the channel can be reached in y); then the wire's lane
    along the channel, up at its pad's column, a short hop over the board, down onto the pad."""
    yl, zl, _ = ln
    p = [np.array(q, float) for q in pre]
    x0, y0, z0 = p[-1]
    pd = pad(pin)
    zh = HOP_EVEN if pin % 2 == 0 else HOP_ODD
    rx = pd[0] + (0.55 if pin % 2 else -0.55)        # odd / even pins of a column climb 1.1 mm apart
    return p + [(x0, yl, z0), (x0, yl, zl), (rx, yl, zl), (rx, yl, zh), (pd[0], pd[1] + (0.8 if pin % 2 == 0 else -0.8), zh), pd]

# fixed places inside the 8.4 mm hinge bore / cheek channel for the four cables that go through it
HINGE_SLOT = {"hdmi": (0.0, 2.2), "coax": (0.0, -2.4), "5v": (-2.4, 0.0), "gnd": (2.4, 0.0)}

def hinge_base(ln, frm, slot, xl=None):
    """from a channel point, along this wire's lane, through the box and cheek B into the hinge bore."""
    yl, zl, xl0 = ln
    xl = xl0 if xl is None else xl
    dy, dz = HINGE_SLOT[slot]
    cx = sum(B.CHEEK_B_CHANNEL) / 2
    return [frm, (frm[0], yl, zl), (xl, yl, zl), (xl, 60.5, zl), (xl, 63.5, zl),
            (cx + dz * 0.9, hy + dy, 14.0), (cx + dz * 0.9, hy + dy, 20.0), (cx + dz * 0.3, hy + dy, hz + dz)]

LID_RUN_Z = {"hdmi": 36.6, "5v": 34.9, "gnd": 33.2, "coax": 31.4}   # each its own height in the lid

def hinge_lid(slot, end):
    dy, dz = HINGE_SLOT[slot]
    lx = sum(B.LID_CABLE_X) / 2
    zr = LID_RUN_Z[slot]
    return [(81.5, hy + dy, hz + dz), (lx + dy * 0.9, hy + dy * 0.3, hz + dz), (lx + dy * 0.9, 61.2, zr),
            (end[0], 61.2, zr), (end[0], end[1] + 1.0, end[2]), end]

# ----------------------------------------------------------------------------------- the plan
P = []
def w(name, kind, a, b, base, lid=None, note=""):
    P.append(dict(name=name, kind=kind, a=a, b=b, base=[np.array(p, float) for p in base],
                  lid=[np.array(p, float) for p in lid] if lid else None, note=note))

import layout as _L
_tx = _L.TP4056_SHIFT_X
TP = dict(bp=(8.0 + _tx, 29.5, 19.4), bn=(11.0 + _tx, 29.5, 19.4), op=(16.0 + _tx, 29.5, 19.4), on=(19.0 + _tx, 29.5, 19.4))
_bx, _by, _bz = BOOST["x0"], BOOST["y0"], BOOST["z0"] + BOOST["pcb"]
_bpy = _by + BOOST["size"][1] - 1.2                     # its pads, along the back edge (past the charger's edge)
BST = dict(vin=(_bx + 2.5, _bpy, _bz), gin=(_bx + 5.0, _bpy, _bz), gout=(_bx + 10.0, _bpy, _bz), vout=(_bx + 12.5, _bpy, _bz))
S5 = np.array([25.6, YB - 1.0, 11.6])          # 5 V splice (heat-shrunk), just behind the Radxa
SG = np.array([25.6, YB + 1.0, 11.6])          # GND splice

# --- power
ln = lane()
w("BAT+", "pwr", "18650 + contact (right end)", "TP4056 B+",
  [(bt.POS_SLOT_X + 1.0, bt.YC, B.CV_Z0 - 0.7), (77.6, bt.YC, 20.6), (77.6, 37.0, ln[1]), (77.6, ln[0], ln[1]),
   (23.9, ln[0], ln[1]), (23.9, 36.9, 20.9), (20.0, 32.5, 20.9), (TP["bp"][0], 31.0, 20.2), TP["bp"]],
  note="24 AWG silicone, red")
w("BAT-", "gnd", "18650 - contact (door spring)", "TP4056 B-",
  [(bt.WIRE_X_IN, bt.YC - 6.0, bt.WIRE_Z), (bt.WIRE_X_IN, 36.6, bt.WIRE_Z), (TP["bn"][0], 31.0, 20.0), TP["bn"]],
  note="24 AWG black - through the hole in the chamber divider")
# load path: TP4056 B+/B- pads (battery side, past its ~3 A protection) -> power switch -> Pololu U3V40F5 -> splices
import switch as SW
_pz = SW.ZC; _px = SW.X1 + SWITCH["pins"][2] - 0.3
w("B+ -> switch", "pwr", "TP4056 B+", "power switch middle pin (common)",
  [TP["bp"], (TP["bp"][0], 29.5, 20.6), (10.4, SWITCH["y"], 20.9), (_px, SWITCH["y"], _pz)],
  note="20-22 AWG red, over the top of the charger (battery side: the TP4056's protection is not in the load path)")
w("switch -> boost VIN", "pwr", "power switch outer pin (the ON end)", "BOOST VIN",
  [(_px, SWITCH["y"] + SWITCH["pins"][1], _pz), (9.8, SWITCH["y"] + SWITCH["pins"][1], 21.0), (9.8, 31.6, 20.9),
   (8.6, 33.2, 17.5), (BST["vin"][0], _bpy + 0.6, 13.0), BST["vin"]],
  note="20-22 AWG red; check with a multimeter which outer pin is ON with the knob toward the back")
w("B- -> boost GND", "gnd", "TP4056 B-", "BOOST GND (in)",
  [TP["bn"], (TP["bn"][0], 31.6, 19.0), (BST["gin"][0], _bpy + 0.6, 13.6), BST["gin"]],
  note="20-22 AWG black")
w("input cap +", "pwr", "input capacitor + (47 uF)", "BOOST VIN",
  [(BST["vin"][0] - 0.6, _bpy + 2.6, _bz + 3.2), (BST["vin"][0] - 0.3, _bpy + 0.8, _bz + 1.0), BST["vin"]],
  note="47 uF 10 V low-ESR electrolytic or ceramic right at the input pads (Pololu's advice for long battery leads)")
w("input cap -", "gnd", "input capacitor - (47 uF)", "BOOST GND (in)",
  [(BST["gin"][0] + 0.6, _bpy + 2.6, _bz + 3.2), (BST["gin"][0] + 0.3, _bpy + 0.8, _bz + 1.0), BST["gin"]],
  note="(the capacitor's other leg)")
w("boost 5V -> splice", "pwr", "BOOST VOUT (fixed 5 V)", "5 V splice",
  [BST["vout"], (BST["vout"][0], _bpy + 1.2, _bz + 1.6), (23.0, S5[1], S5[2] + 0.6), S5],
  note="20-22 AWG red - one thick lead, split at a heat-shrunk splice behind the Radxa")
w("boost GND -> splice", "gnd", "BOOST GND (out)", "GND splice",
  [BST["gout"], (BST["gout"][0], _bpy + 1.2, _bz + 1.0), (23.0, SG[1], SG[2] - 0.6), SG],
  note="20-22 AWG black")
ln = lane(); w("5V -> Radxa", "pwr", "5 V splice", "Radxa pin 2 (+5V)", header(2, [S5], ln), note="24 AWG")
ln = lane(); w("GND -> Radxa", "gnd", "GND splice", "Radxa pin 6 (GND)", header(6, [SG], ln), note="24 AWG")
ln = lane(); w("Screen 5V", "pwr", "5 V splice", "driver board 5V (USB-C pads)", hinge_base(ln, S5, "5v"),
               hinge_lid("5v", (40.0, 56.8, 35.5)), note="24-26 AWG, through the hinge")
ln = lane(); w("Screen GND", "gnd", "GND splice", "driver board GND", hinge_base(ln, SG, "gnd"),
               hinge_lid("gnd", (42.0, 56.8, 35.5)), note="24-26 AWG, through the hinge")

# --- I2C: Radxa -> PN532 -> CardKB (chained at the PN532's header pins)
import layout as _Lp
PNP = (69.5 + _Lp.PN532_SHIFT_X, 33.0, 7.6)       # PN532 header (moves with the board)
for i, (sig, pin, kind) in enumerate((("SCL", 29, "i2c"), ("SDA", 31, "i2c"), ("3V3", 17, "v33"), ("GND", 25, "gnd"), ("IRQ", 36, "gpio"))):
    x = PNP[0] + (i - 2) * 0.9
    w(f"PN532 {sig}", kind, f"PN532 {sig} (DIP switches: I2C)", f"Radxa pin {pin}",
      header(pin, [(x, PNP[1], PNP[2])], lane()), note="28-30 AWG")
for i, sig in enumerate(("SCL", "SDA", "3V3", "GND")):
    x = GP[0] + (i - 1.5) * 0.9
    yl, zl, _ = lane()
    px = PNP[0] + (i - 2) * 0.9
    w(f"CardKB {sig}", {"SCL": "i2c", "SDA": "i2c", "3V3": "v33", "GND": "gnd"}[sig],
      f"CardKB Grove pad {sig} (underside)", f"PN532 {sig} pin (chain)",
      [(x, GP[1], B.KB_Z - 0.6), (x, bt.TUN_Y0 - DIVIDER - 0.6, B.KB_Z - 0.6), (x, 36.6, 20.6 - i * 0.9),
       (24.0 + i * 0.9, 36.6, 20.6 - i * 0.9), (24.0 + i * 0.9, yl, zl), (px + 0.45, yl, zl), (px + 0.45, PNP[1] + 0.6, PNP[2] + 0.7)],
      note="28-30 AWG; out of the keyboard through the groove, chained onto the PN532's pins")

# --- I2S DAC (PCM5102)
DACP = (52.0, 20.6, 17.4)
for i, (sig, pin, kind) in enumerate((("BCK", 12, "i2s"), ("LRCK", 35, "i2s"), ("DIN", 40, "i2s"), ("VIN 3V3", 1, "v33"), ("GND", 30, "gnd"))):
    x = DACP[0] + (i - 2) * 0.9
    w(f"DAC {sig}", kind, f"PCM5102 {sig}", f"Radxa pin {pin}",
      header(pin, [(x, DACP[1], DACP[2]), (x, 26.0, 15.0)], lane()),
      note="28-30 AWG; DAC module: SCK to GND, FMT low, XSMT high")

# --- GPS (UART3), powered from 5 V (its regulator) so it needs no 3.3 V pad
GPSP = (bt.END_X + GPS_EDGE["gap"] + 2.6, B.GPS_Y0 + 0.6, FLOOR + 0.3 + GPS_MODULE[0] - 1.2)   # pads at its top edge
for i, (sig, pin, kind) in enumerate((("TX -> Radxa RX", 3, "uart"), ("RX <- Radxa TX", 5, "uart"), ("VCC 5V", 4, "pwr"), ("GND", 9, "gnd"))):
    x = GPSP[0] + (i - 1.5) * 0.9
    w(f"GPS {sig}", kind, f"GPS module {sig.split()[0]}", f"Radxa pin {pin}",
      header(pin, [(x, GPSP[1], GPSP[2]), (x, 36.6, GPSP[2]), (x, 36.6, 9.0)], lane()), note="28-30 AWG")

# --- LoRa E22 (UART4) + mode pins; VCC from the 5 V splice
LRP = (63.0, 22.1, 10.6)
for i, (sig, pin, kind) in enumerate((("TXD -> Radxa RX", 16, "uart"), ("RXD <- Radxa TX", 18, "uart"), ("M0", 13, "gpio"),
                                      ("M1", 7, "gpio"), ("AUX", 22, "gpio"), ("GND", 34, "gnd"))):
    x = LRP[0] + (i - 2.5) * 0.9
    w(f"LoRa {sig}", kind, f"E22 {sig.split()[0]}", f"Radxa pin {pin}",
      header(pin, [(x, LRP[1], LRP[2]), (x, 27.0, 12.5)], lane()), note="28-30 AWG")
yl, zl, _ = lane()
w("LoRa VCC 5V", "pwr", "5 V splice", "E22 VCC",
  [S5, (S5[0], yl, zl), (LRP[0] + 3.2, yl, zl), (LRP[0] + 3.2, 27.0, 12.5), (LRP[0] + 3.2, LRP[1], LRP[2])],
  note="24-26 AWG")

# --- SDR (NESDR Nano 2+, USB plug cut off) on USB2 HOST2 = header pins 27/28 (resistor swap)
SDRP = (SDR_BODY[3] + 0.3, (SDR_BODY[1] + SDR_BODY[4]) / 2, 12.0)
def sdr_pre(dy, ln):
    yl, zl, xl = ln
    return [(SDRP[0], SDRP[1] + dy, SDRP[2] + dy), (60.0, 69.0 + dy, 9.0 + dy), (xl, 66.0, 8.0 + 1.1 * (dy + 2)),
            (xl, 60.5, zl), (xl, 37.0, zl)]
for i, (sig, pin, kind) in enumerate((("D+", 27, "usb"), ("D-", 28, "usb"), ("GND", 14, "gnd"))):
    ln = lane()
    w(f"SDR {sig}", kind, f"SDR USB {sig} (plug removed)", f"Radxa pin {pin}",
      header(pin, sdr_pre((i - 1) * 0.9, ln), ln),
      note="D+/D- as a twisted pair, keep it short; 28 AWG" if kind == "usb" else "24-26 AWG")
ln = lane()
w("SDR 5V", "pwr", "5 V splice", "SDR USB VBUS",
  list(reversed([np.array(p) for p in sdr_pre(1.8, ln)])) + [] if False else
  [S5, (S5[0], ln[0], ln[1]), (ln[2], ln[0], ln[1]), (ln[2], 60.5, ln[1]), (ln[2], 66.0, 12.4),
   (60.0, 70.8, 10.8), (SDRP[0], SDRP[1] + 1.8, SDRP[2] + 1.8)], note="24-26 AWG")

# --- HDMI ribbon (soldered at the Radxa end) and coax
HD0 = np.array([sum(_rp["hdmi"]) / 2, 3.0, _rp["z"][0] - 0.3])
ln = lane()
w("HDMI ribbon", "hdmi", "Radxa micro-HDMI (soldered)", "driver board mini-HDMI (C2 plug)",
  [HD0, (HD0[0], 12.0, 13.2), (HD0[0], 26.0, 13.2)] + hinge_base(ln, np.array((HD0[0], 26.0, 13.2)), "hdmi", xl=77.4)[1:],
  hinge_lid("hdmi", (32.0, 57.0, 35.0)), note="FPV FPC ribbon, rolled through the 8.4 mm hinge bore")
ln = lane()
w("GPS antenna coax", "coax", "GPS module u.FL", "patch antenna (lid)",
  [(GPSP[0] + 1.4, GPSP[1] + 8.0, GPSP[2] - 3.0), (GPSP[0] + 1.4, 36.6, GPSP[2] - 3.0), (GPSP[0] + 1.4, 36.6, 9.5)] + hinge_base(ln, np.array((GPSP[0] + 1.4, 36.6, 9.5)), "coax")[1:],
  hinge_lid("coax", (Ld.PATCH_X0 + 9.4, 49.5, 37.4)), note="1.13 mm u.FL-u.FL coax, ~150 mm")
ln = lane()
w("LoRa antenna coax", "coax", "E22 u.FL", "LoRa FPC antenna (box back wall)",
  [(LRP[0] + 1.5, 14.0, 10.0), (69.6, 14.0, 10.0), (69.6, 27.0, 12.5), (69.6, ln[0], ln[1]), (ln[2], ln[0], ln[1]),
   (ln[2], 60.5, ln[1]), (ln[2], 77.5, 6.0), (40.0, 78.6, 9.0), (31.0, 79.3, 17.0)],
  note="1.13 mm u.FL coax, ~120 mm (Molex 211140 has its own 100 mm lead)")
ln = lane()
w("Wi-Fi antenna coax", "coax", "Radxa u.FL (Wi-Fi)", "Wi-Fi FPC antenna (box roof)",
  [(_b[3] - 58.0, 9.0, _ZP + 0.2), (34.0, 9.0, 13.0), (34.0, ln[0], ln[1]), (ln[2], ln[0], ln[1]),
   (ln[2], 60.5, ln[1]), (ln[2], 76.0, 19.5), (65.0, 75.0, 22.3)],
  note="1.13 mm u.FL coax; enable the external antenna overlay in rsetup")

COLORS = dict(usb="#9d4edd", pwr="#d62828", gnd="#1b1b1b", v33="#f77f00", i2c="#277da1", i2s="#43aa8b", uart="#f9c74f",
              gpio="#f2f2f2", hdmi="#c46b2c", coax="#8d99ae")
RADIUS = dict(usb=0.3, pwr=0.45, gnd=0.45, v33=0.3, i2c=0.3, i2s=0.3, uart=0.3, gpio=0.3, hdmi=0.9, coax=0.56)

def tube(points, r):
    pts = np.array(points, float)
    keep = [0] + [i for i in range(1, len(pts)) if np.linalg.norm(pts[i] - pts[i - 1]) > 1e-6]
    pts = pts[keep]
    if len(pts) < 2:
        return None
    line = pv.lines_from_points(pts)
    return line.tube(radius=r, n_sides=10, capping=True)

def build():
    groups = {}
    for wd in P:
        for part, pts in (("base", wd["base"]), ("lid", wd["lid"])):
            if not pts:
                continue
            t = tube(pts, RADIUS[wd["kind"]])
            if t is not None:
                groups.setdefault((part, wd["kind"]), []).append(t)
    files = []
    for (part, kind), ts in groups.items():
        m = ts[0].merge(ts[1:]) if len(ts) > 1 else ts[0]
        f = f"out/parts_in_place/wires_{part}_{kind}.stl"
        m.extract_surface().triangulate().save(f)
        files.append((f, part, kind))
    return files

def write_plan():
    pins = {}
    for wd in P:
        if wd["b"].startswith("Radxa pin"):
            pins.setdefault(int(wd["b"].split()[2]), []).append(wd["name"])
    L_ = ["# Minideck wiring plan", "",
          "Radxa ZERO 3W, mounted upside down: the 40 header pads (no header fitted) face UP under the",
          "keyboard - solder wires on that side and lay them flat (~3 mm of room above the board).",
          "Pin 1 is at the microSD end (Pi-Zero layout). Radxa's board drawing puts the microSD socket at the",
          "board's **left** end in this case (the camera FPC is at the right end), so pin 1 is at the left end.",
          "The 3D wire routes in the viewer were drawn with pin 1 at the right end: go by the pin numbers below,",
          "not the 3D routes, and check the square pad / '1' mark on your board before soldering.", "",
          "## Radxa header use", "", "| Pin | Function | Wires |", "|---|---|---|"]
    fn = {1: "3V3", 2: "5V", 3: "GPIO1_A0 / UART3 RX", 4: "5V", 5: "GPIO1_A1 / UART3 TX", 6: "GND",
          7: "GPIO3_C4", 9: "GND", 12: "GPIO3_A3 / I2S3 SCLK (BCK)", 13: "GPIO3_A2", 14: "GND",
          16: "GPIO3_B1 / UART4 RX", 17: "3V3", 18: "GPIO3_B2 / UART4 TX", 20: "GND", 22: "GPIO3_C1",
          25: "GND", 27: "USB2 HOST2 D+ (after R32->R45 swap)", 28: "USB2 HOST2 D- (after R39->R46 swap)",
          29: "GPIO3_B3 / I2C5 SCL", 30: "GND", 31: "GPIO3_B4 / I2C5 SDA", 34: "GND",
          35: "GPIO3_A4 / I2S3 LRCK", 36: "GPIO3_A7", 40: "GPIO3_A5 / I2S3 SDO (DIN)"}
    for p in sorted(pins):
        L_.append(f"| {p} | {fn.get(p, '')} | {', '.join(pins[p])} |")
    L_ += ["", "## Every wire", "", "| Wire | From | To | Type / note |", "|---|---|---|---|"]
    for wd in P:
        L_.append(f"| {wd['name']} | {wd['a']} | {wd['b']} | {wd['note']} |")
    L_ += ["", "## Notes", "",
           "- **Power switch**: an SS12D00 slide switch (SPDT, 8.6 x 3.6 mm body) in the left wall, beside the TP4056, "
           "breaks TP4056 B+ -> boost VIN. Middle pin = from the charger's B+ pad, one outer pin = to the boost (the other "
           "outer pin stays empty). The printed pill knob (print/yellow/switch_knob.stl) presses onto its lever. "
           "Charging still works with the switch off (the TP4056 charges the cell directly).",
           "- **5 V boost: Pololu U3V40F5** (fixed 5 V, ~2.6 A from a charged cell, ~2.1 A near empty). It is fed from the TP4056's "
           "B+/B- pads so the TP4056's ~3 A protection is out of the load path: use a **protected high-drain 18650** (button top, "
           "<= 70 mm, protection >= 5 A, e.g. Nitecore NL1835HP or Keeppower 3500 protected). The TP4056 now only charges; its OUT pads stay empty. "
           "47 uF on the boost input. Have the Radxa shut down cleanly near 3.2-3.3 V cell voltage.",
           "- One wire per Radxa pad. I2C (CardKB 0x5F, PN532 0x24) on I2C5 (pins 29/31) runs Radxa -> PN532, and the "
           "CardKB is chained onto the PN532's header pins. Power both from 3.3 V (pin 17) so the bus pull-ups stay at "
           "3.3 V (the Radxa is not 5 V tolerant). Enable the i2c5 overlay.",
           "- 5 V: one 22 AWG lead from the boost to a heat-shrunk splice just behind the Radxa, branching to Radxa pin 2, "
           "the LoRa, the screen and the SDR. Same for GND (Radxa pin 6 + screen). The GPS runs from 5 V on pin 4 "
           "(its module has a regulator; its UART stays 3.3 V).",
           "- DAC: I2S3 (pins 12/35/40), enable the i2s3 overlay; tie the module's SCK to GND.",
           "- GPS on UART3 (pins 3/5), LoRa E22 on UART4 (pins 15/17); M0/M1/AUX on pins 13/7/22. "
           "Pins 8/10 (UART2) are the debug console - left free.",
           "- Screen: HDMI ribbon + its own 5 V pair straight from the boost, all through the hinge bore.",
           "- SDR on header pins 27/28 = the RK3566's spare USB2 HOST2 port (schematic page 20). On the Radxa: "
           "remove R32 and R39 (0 ohm, they route I2C4 to those pins) and fit 0 ohm / a solder bridge on R45 and "
           "R46 (marked NC). Cut the dongle's USB-A plug off and solder VBUS/D-/D+/GND straight to pins 2/28/27/14. "
           "Keep D+/D- twisted and short. Software: the HOST2 (EHCI/OHCI) controller must be enabled in the "
           "device tree - check rsetup overlays, or ask me for an overlay.",
           "- Pin map checked against Radxa's schematic (page 20): 3V3 = pins 1 & 17; UART4 RX/TX = 16/18; "
           "GND = 6, 9, 14, 20, 25, 30, 34, 39 (the web pin table has some of these wrong).",
           "- Wire: 24 AWG silicone for power, 28-30 AWG silicone for signals, 1.13 mm coax for antennas.",
           "- The CardKB Grove pads sit over the battery block: a 1.2 mm groove in its top lets those 4 wires out."]
    open("WIRING.md", "w").write("\n".join(L_) + "\n")
    import json                                          # structured copy for the Obsidian canvas diagrams
    json.dump([dict(name=wd["name"], kind=wd["kind"], a=wd["a"], b=wd["b"], note=wd["note"]) for wd in P],
              open("out/wires.json", "w"), indent=1)

if __name__ == "__main__":
    files = build()
    write_plan()
    for f, part, kind in files:
        print(part, kind, f)
    print("pad 1", np.round(pad(1), 2), "pad 40", np.round(pad(40), 2), "grove pads", np.round(GP, 2))
