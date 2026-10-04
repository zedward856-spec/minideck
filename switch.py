"""Power switch: an SS12D00 slide switch inside the left wall, beside the TP4056, with a printed pill knob.

    import switch;  b += switch.case_adds();  b -= switch.case_cuts()
    python3 switch.py   -> out/switch_knob.stl (print face down), out/parts_in_place/{switch_knob,power_switch}.stl
"""
from build123d import Box, Pos, Align, Cylinder, Rot, export_stl, Sketch, SlotOverall, extrude, Plane
from params import *

A0 = (Align.MIN, Align.MIN, Align.MIN)
S = SWITCH
BL, BH, BW = S["body"]                       # 8.6 along y, 3.5 along x, 3.6 along z
X0 = S["face_x"]                            # body face (lever side), against the wall's inside
X1 = X0 + BH                                 # body back (pins side)
Z1 = S["top"]; Z0 = Z1 - BW; ZC = (Z0 + Z1) / 2
Y0, Y1 = S["y"] - BL / 2, S["y"] + BL / 2
C = S["clr"]

def box(x0, y0, z0, x1, y1, z1):
    return Pos(x0, y0, z0) * Box(x1 - x0, y1 - y0, z1 - z0, align=A0)

def pill_x(x0, x1, yc, zc, length, height):
    """a stadium (pill) prism along x: rounded ends along y"""
    sk = Plane.YZ.offset(x0) * Pos(yc, zc) * SlotOverall(length, height)
    return extrude(sk, x1 - x0)

def body(at=0.0):
    """the switch itself (viewer / checks), lever at position `at` (-1 .. +1 = one end .. other)"""
    b = box(X0, Y0, Z0, X1, Y1, Z1)
    ly = S["y"] + at * S["travel"] / 2
    lw, lt, ll = S["lever"]
    b += box(X0 - ll, ly - lw / 2, ZC - lt / 2, X0, ly + lw / 2, ZC + lt / 2)
    n, pitch, plen, ps = S["pins"]
    for k in range(n):
        py = S["y"] + (k - (n - 1) / 2) * pitch
        b += box(X1, py - ps / 2, ZC - ps / 2, X1 + plen, py + ps / 2, ZC + ps / 2)
    return b

def pill_z(x0, x1, yc, zc, width, height):
    """a vertical pill (rounded top and bottom) prism along x"""
    sk = Plane.YZ.offset(x0) * Pos(yc, zc) * Rot(0, 0, 90) * SlotOverall(height, width)
    return extrude(sk, x1 - x0)

def knob(at=0.0):
    """the knob: a pill plate that sits in the pocket on the wall's INSIDE (bigger than the outside slot, so it
    can't come out), and a thin vertical fin through the outer skin, its top level with the outside face. The
    lever socket is open at the top, so the switch drops straight down into it."""
    kl, kh, kt = S["knob"]; fw, fh = S["fin"]; sk = S["skin"]
    yc = S["y"] + at * S["travel"] / 2
    xb = X0 - 0.05                            # plate back, just off the switch face
    k = pill_x(xb - kt, xb, yc, ZC, kl, kh)
    k += pill_z(0.0, xb - kt + 0.01, yc, ZC, fw, fh)      # fin: plate -> through the skin -> flush at x = 0
    lw, lt, ll = S["lever"]
    k -= box(X0 - ll - 0.05, yc - lw / 2 - C, ZC - lt / 2 - C, xb + 0.01, yc + lw / 2 + C, ZC + kh)   # socket, open on top
    return k

def slot_size():
    fw, fh = S["fin"]
    return fw + S["travel"] + 2 * C, fh + 2 * C       # outside slot: the fin and its travel only

def case_cuts():
    kl, kh, kt = S["knob"]; tr = S["travel"]; sk = S["skin"]; lw, lt, ll = S["lever"]
    c = box(X0 - 0.01, Y0 - C, Z0 - C, X1 + 0.5, Y1 + C, Z1 + 0.3)                        # body space (+ ledge)
    c += pill_x(sk, WALL + 0.01, S["y"], ZC, kl + tr + 2 * C, kh + 2 * C)                  # knob pocket, open inside
    fw, fh = S["fin"]                                                                       # outside slot: the fin
    for e in (-1, 1):                                                                       # swept along its travel
        c += pill_z(-1, sk + 0.01, S["y"] + e * tr / 2, ZC, fw + 2 * C, fh + 2 * C)
    c += box(-1, S["y"] - tr / 2, ZC - fh / 2 - C, sk + 0.01, S["y"] + tr / 2, ZC + fh / 2 + C)
    c += box(X0 - ll - 2 * C, S["y"] - (lw + tr) / 2 - C, ZC, WALL + 0.01,                 # groove: the lever drops
             S["y"] + (lw + tr) / 2 + C, TOP_Z + 1)                                         # down into the knob
    half = kl / 2 + tr / 2 + 0.6                                                            # access channel: the knob
    c += box(WALL - 0.01, S["y"] - half, ZC - kh / 2 - C, 5.8, S["y"] + half, TOP_Z + 1)   # drops in from the top
    return c

def pocket_footprint():
    """outside-face (y, z) area with thin wall behind it (knob pocket + lever groove): stripes keep off it"""
    from shapely.geometry import LineString, box as sb
    kl, kh = S["knob"][:2]; tr = S["travel"]; lw = S["lever"][0]
    L, H = kl + tr + 2 * C, kh + 2 * C
    pocket = LineString([(S["y"] - L / 2 + H / 2, ZC), (S["y"] + L / 2 - H / 2, ZC)]).buffer(H / 2, 32)
    groove = sb(S["y"] - (lw + tr) / 2 - C, ZC, S["y"] + (lw + tr) / 2 + C, TOP_Z + 1)
    return pocket.union(groove)

def case_adds():
    """a block under the switch body (grows from the floor beside the charger / boost), kept below the knob
    pocket so the knob can be slid in from inside; the switch is held with a dab of hot glue"""
    return box(WALL - 0.01, Y0 - 1.0, FLOOR - 0.01, 4.0, Y1 + 1.0, Z0 - C)

if __name__ == "__main__":
    export_stl(knob(-1), "out/parts_in_place/switch_knob.stl")        # shown in the OFF position
    export_stl(body(-1), "out/parts_in_place/power_switch.stl")
    k = knob(0); bb = k.bounding_box()
    export_stl(Rot(0, 90, 0) * Pos(-bb.max.X, -S["y"], -ZC) * k, "out/switch_knob.stl")    # flat back on the bed, ridge up
    print("switch body x", round(X0, 2), round(X1, 2), "z", round(Z0, 2), round(Z1, 2), "y", Y0, Y1)
    print("knob", round(bb.size.X, 2), "x", round(bb.size.Y, 2), "x", round(bb.size.Z, 2), "| fin top at x", round(bb.min.X, 3),
          "(0 = flush) | lever tip at x", round(X0 - S["lever"][2], 2), "| outside slot", [round(v, 2) for v in slot_size()],
          "| plate", S["knob"][:2])
