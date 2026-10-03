"""Power switch: an SS12D00 slide switch inside the left wall, beside the TP4056, with a printed pill knob.

    import switch;  b += switch.case_adds();  b -= switch.case_cuts()
    python3 switch.py   -> out/switch_knob.stl (print face down), out/parts_in_place/{switch_knob,power_switch}.stl
"""
from build123d import Box, Pos, Align, Cylinder, Rot, export_stl, Sketch, SlotOverall, extrude, Plane
from params import *

A0 = (Align.MIN, Align.MIN, Align.MIN)
S = SWITCH
BL, BH, BW = S["body"]                       # 8.6 along y, 3.5 along x, 3.6 along z
X0 = WALL - S["wall_pocket"]                 # body face (lever side), sunk into the wall
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

def knob(at=0.0):
    """pill knob on the lever: sits in a shallow recess, a taller pill ridge in the middle"""
    kl, kh, kt = S["knob"]; rl, rh, rt = S["ridge"]
    yc = S["y"] + at * S["travel"] / 2
    xb = S["recess"] - C                     # its back, just off the recess floor
    k = pill_x(xb - kt, xb, yc, ZC, kl, kh)
    k += pill_x(xb - kt - rt, xb - kt + 0.01, yc, ZC, rl, rh)
    lw, lt, ll = S["lever"]
    k -= box(X0 - ll - 0.1, yc - lw / 2 - C, ZC - lt / 2 - C, xb + 0.01, yc + lw / 2 + C, ZC + lt / 2 + C)   # lever socket
    return k

def case_cuts():
    kl, kh, kt = S["knob"]; lw, lt, ll = S["lever"]; tr = S["travel"]
    c = box(X0 - 0.01, Y0 - C, Z0 - C, X1 + 0.5, Y1 + C, Z1 + 0.3)                        # body pocket (+ ledge)
    c += box(-1, S["y"] - (lw + tr) / 2 - 0.2, ZC - lt / 2 - 0.2, X0 + 0.01,              # lever slot
             S["y"] + (lw + tr) / 2 + 0.2, ZC + lt / 2 + 0.2)
    c += pill_x(-1, S["recess"], S["y"], ZC, kl + tr + 2 * C + 0.4, kh + 2 * C + 0.2)    # knob recess
    c += box(WALL - 0.01, Y0 - 1.2, 21.7, 6.5, Y1 + 1.2, 22.72)                           # keyboard ledge over it
    return c

def case_adds():
    """a block under the body (grows from the floor, beside the charger / boost) and end stops"""
    a = box(WALL - 0.01, Y0 - 1.0, FLOOR - 0.01, 4.0, Y1 + 1.0, Z0 - C)
    a += box(WALL - 0.01, Y0 - 1.0 - C, FLOOR - 0.01, 4.0, Y0 - C, Z1 - 0.4)
    a += box(WALL - 0.01, Y1 + C, FLOOR - 0.01, 4.0, Y1 + 1.0 + C, Z1 - 0.4)
    return a

if __name__ == "__main__":
    export_stl(knob(-1), "out/parts_in_place/switch_knob.stl")        # shown in the OFF position
    export_stl(body(-1), "out/parts_in_place/power_switch.stl")
    k = knob(0); bb = k.bounding_box()
    export_stl(Rot(0, 90, 0) * Pos(-bb.max.X, -S["y"], -ZC) * k, "out/switch_knob.stl")    # flat back on the bed, ridge up
    print("switch body x", round(X0, 2), round(X1, 2), "z", round(Z0, 2), round(Z1, 2), "y", Y0, Y1)
    print("knob", round(bb.size.X, 2), "x", round(bb.size.Y, 2), "x", round(bb.size.Z, 2), "sticks out", round(-bb.min.X, 2), "mm")
