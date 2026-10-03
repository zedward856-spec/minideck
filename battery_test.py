"""Round 18650 chamber + hinged side door (left end of the base).

The door swings on a vertical hinge at its front edge (pin = a 1.75 mm piece of filament) and
clicks shut with a hook at its back edge, so the rounded back corner of the case stays whole. The - spring plate sits in a slot in the door; the
+ plate sits behind a 0.8 mm wall with a 7 mm hole, so a backwards cell never touches it.

    python3 battery_test.py   -> out/battery_strip_test.stl, out/battery_door.stl
"""
import math
from build123d import (Align, Box, Cylinder, Pos, Rot, Plane, Polyline, make_face, extrude,
                       export_stl, export_step)
from params import *

MIN = (Align.MIN, Align.MIN, Align.MIN)
CEN = (Align.CENTER, Align.CENTER, Align.MIN)


def box(x0, y0, z0, x1, y1, z1):
    return Pos(x0, y0, z0) * Box(x1 - x0, y1 - y0, z1 - z0, align=MIN)


def cyl_x(x0, x1, y, z, d):
    return Pos(x0, y, z) * Rot(0, 90, 0) * Cylinder(d / 2, x1 - x0, align=CEN)


def cyl_y(y0, y1, x, z, d):
    return Pos(x, y0, z) * Rot(-90, 0, 0) * Cylinder(d / 2, y1 - y0, align=CEN)


def cyl_z(x, y, z0, z1, d):
    return Pos(x, y, z0) * Cylinder(d / 2, z1 - z0, align=CEN)


# chamber axis: where the user placed the battery
R = BORE / 2
YC = CH_YC
ZC = CH_ZC

# along X from the door
DOOR_SLOT_X0 = 0.5                                  # - plate slot inside the door
NEG_X = DOOR_SLOT_X0 + PLATE_SLOT + SPRING_SPACE
SHOULDER_X = NEG_X + CELL_L - CELL_BUTTON
POS_SLOT_X = SHOULDER_X + BLOCKER_T
END_X = POS_SLOT_X + PLATE_SLOT + BACKWALL_T
SLOT_HALF_W = (PLATE_W + 0.4) / 2
SLOT_Z0 = ZC - (PLATE_H + 0.4) / 2

# door recess and hinge (hinge on the door's FRONT edge, just in front of the chamber)
REC_Y1 = YC + R + 0.4
REC_Z1 = CV_Z0 - 0.1                            # door covers the chamber up to the keyboard
HX, HY = 1.7, TUN_Y0 + 0.1 - DOOR_KNUCKLE_R
KR = DOOR_KNUCKLE_R
CASE_KNUCKLES = [(FLOOR, 6.0), (16.6, REC_Z1)]
DOOR_KNUCKLE = (6.3, 16.3)
DOOR_Y0 = HY + KR + 0.3
PIN_Z0 = 0.6                                    # 0.6 mm skin under the pin
PIN_Z1 = KB_Z + PLATE_UNDER + 0.5               # through the top of the wall (under the plate)


# up/down lock: a tab on the door's back edge reaches into the case. A one-piece C-clip slider sits
# in a flush pocket behind it: its C-shaped back snaps over a vertical T-rail (push it on from the
# left), so it can only slide up and down. Down = it covers the tab (door can't open), up = it
# clears the tab and the door swings free. A bump on the rail clicks into a dimple at each end.
LOCK_Z = 6.0                                     # tab centre height
TAB = (0.9, 1.6, 4.0)                            # tab: outer face x, reach into the case, height
FLANGE = (0.8, 1.9)                              # front part over the tab: thickness, depth (y)
LOCK_BODY = (7.5, 11.8)                          # clip part depth (y), slider height
LOCK_TRAVEL = TAB[2] + 0.4                       # up to unlock
LOCK_ZB = LOCK_Z - TAB[2] / 2 - 0.2              # slider bottom, locked
LOCK_Y0 = REC_Y1                                 # slider front
LOCK_BY0 = LOCK_Y0 + FLANGE[1]                   # clip part front
LOCK_REC_Y1 = LOCK_BY0 + LOCK_BODY[0] + 0.2
# C-clip cross-section, x from the outer face, y from LOCK_BY0:
CLIP_PLATE = 0.8                                 # outer plate thickness (flush face)
CLIP_ARM = (0.8, 4.6)                            # arm thickness (y), arm reach (x)
CLIP_LIP = (3.8, 0.6, 0.1)                       # lip catch face x, lip reach (y), lip tip at the ramp end
RAIL_HEAD = (1.05, 3.6, 1.0, 6.5)                # x0, x1, y0, y1 (0.2 clear of plate, arms, lips)
RAIL_NECK = (2.2, 5.3)                           # y0, y1
POCKET_D = 5.0                                   # pocket floor depth
DETENT = (3.75, 5.9, 0.5, 0.3)                   # y, lower dimple z (from slider bottom), radius, bump height
                                                 # (one bump on the rail, two dimples in the clip)


def _xy_prism(pts, z0, z1):
    from build123d import Polyline, make_face, extrude
    return extrude(Plane.XY.offset(z0) * make_face(Polyline(*pts, close=True)), z1 - z0)


def door_lock(at=0.0):
    """The C-clip slider (a plain rectangle from outside), in place; at = 0 locked, LOCK_TRAVEL up."""
    zb, z1 = LOCK_ZB + at, LOCK_ZB + at + LOCK_BODY[1]
    yb, yd = LOCK_BY0, LOCK_BODY[0]
    t, (aw, ax), (lx, lr, lt) = CLIP_PLATE, CLIP_ARM, CLIP_LIP
    s = box(0.05, LOCK_Y0 + 0.1, zb, 0.05 + t, yb + yd, z1)                              # plate
    s += box(0.05 + t - 0.01, yb, zb, ax, yb + aw, z1)                                   # arms
    s += box(0.05 + t - 0.01, yb + yd - aw, zb, ax, yb + yd, z1)
    s += _xy_prism([(lx, yb + aw - 0.01), (lx, yb + aw + lr), (ax, yb + aw + lt), (ax, yb + aw - 0.01)], zb, z1)
    s += _xy_prism([(lx, yb + yd - aw + 0.01), (lx, yb + yd - aw - lr), (ax, yb + yd - aw - lt),
                    (ax, yb + yd - aw + 0.01)], zb, z1)                                  # lips, ramped
    dy, dz, r, h = DETENT
    for k in (0.0, LOCK_TRAVEL):                                                         # dimples
        s -= cyl_x(0.05 + t - h - 0.05, 0.05 + t + 0.1, yb + dy, zb + dz + k, 2 * r + 0.3)
    return s


# groove in the strip top for the 4 CardKB wires (its Grove pads sit right over the battery block)
WIRE_GROOVE = dict(x=8.07, w=4.0, y1=47.3, depth=1.2)


def wire_groove():
    g = WIRE_GROOVE
    return box(g["x"] - g["w"] / 2, TUN_Y0 - DIVIDER - 1.0, CV_Z0 - g["depth"], g["x"] + g["w"] / 2, g["y1"], CV_Z0 + 0.5)


def lock_rail():
    """T-rail the clip snaps over (+ the detent bumps), standing out of the pocket floor."""
    z0, z1 = LOCK_ZB - 0.2, LOCK_ZB + LOCK_TRAVEL + LOCK_BODY[1] + 0.2
    yb = LOCK_BY0
    hx0, hx1, hy0, hy1 = RAIL_HEAD
    c = 0.4                                                                              # lead-in chamfers
    r = _xy_prism([(hx0, yb + hy0 + c), (hx0 + c, yb + hy0), (hx1, yb + hy0), (hx1, yb + hy1),
                   (hx0 + c, yb + hy1), (hx0, yb + hy1 - c)], z0, z1)
    r += box(hx1 - 0.01, yb + RAIL_NECK[0], z0, POCKET_D + 0.2, yb + RAIL_NECK[1], z1)
    dy, dz, rr, h = DETENT
    r += cyl_x(hx0 - h, hx0 + 0.01, yb + dy, LOCK_ZB + dz + LOCK_TRAVEL, 2 * rr)            # bump
    return r


def lock_cuts():
    """The clip's pocket in the case wall (wider behind the face so the arms can snap) + tab slot."""
    z0, z1 = LOCK_ZB - 0.2, LOCK_ZB + LOCK_TRAVEL + LOCK_BODY[1] + 0.2
    yb, yd = LOCK_BY0, LOCK_BODY[0]
    c = box(-1, REC_Y1 - 0.01, z0, 0.05 + CLIP_PLATE + 0.1, yb + yd + 0.15, z1)          # flush opening
    c += box(0.05 + CLIP_PLATE, yb - 0.55, z0, POCKET_D, yb + yd + 0.55, z1)             # undercut
    c += box(TAB[0] - 0.15, REC_Y1 - 0.01, LOCK_Z - TAB[2] / 2 - 0.2, DOOR_T + 0.3,
             REC_Y1 + TAB[1] + 0.2, LOCK_Z + TAB[2] / 2 + 0.2)                          # tab slot
    return c


# - wire: door -> spring space -> straight through the divider to the boards
WIRE_D = 1.8
WIRE_Z = 17.0
WIRE_X_IN = 4.2


def chamber():
    """Round bore with a 45 deg roof ridge cut flat, so it prints without supports."""
    s = cyl_x(-1, SHOULDER_X, YC, ZC, BORE)
    k = R / math.sqrt(2)
    ridge = make_face(Polyline((YC - k, ZC + k), (YC - R * (math.sqrt(2) - 1), ZC + R),
                               (YC + R * (math.sqrt(2) - 1), ZC + R), (YC + k, ZC + k), close=True))
    s += extrude(Plane.YZ.offset(-1) * ridge, SHOULDER_X + 1)
    return s


def strip_solid():
    s = box(0, TUN_Y0 - DIVIDER, 0, END_X, OUT_D, CV_Z0)
    # wall around the door hinge where it pokes into the board zone
    s += box(0, HY - KR - 1.1, 0, HX + KR + 0.7, TUN_Y0, REC_Z1)
    # the PN532's back edge runs under the cell (as placed): leave room for it
    from layout import bounds
    pn = bounds("pn532")
    return s - box(pn[0] - 0.4, pn[1] - 0.4, FLOOR - 0.01, pn[3] + 0.4, pn[4] + 0.4, pn[5] + 0.4)


def strip_cuts():
    s = chamber()
    s += box(-1, HY, FLOOR, DOOR_T, REC_Y1, REC_Z1)                           # door recess
    s += box(-1, HY - KR - 0.3, FLOOR, HX + KR + 0.3, DOOR_Y0, REC_Z1)       # knuckle room
    s += cyl_x(SHOULDER_X - 1, SHOULDER_X + BLOCKER_T + 0.01, YC, ZC, BLOCKER_HOLE)
    s += box(POS_SLOT_X, YC - SLOT_HALF_W, SLOT_Z0,                             # + plate slot,
             POS_SLOT_X + PLATE_SLOT, YC + SLOT_HALF_W, CV_Z0 + 1)            # drops in from the top
    s += box(POS_SLOT_X, YC - 3, CV_Z0 - 1.4, END_X + 0.1, YC + 3, CV_Z0)      # + tab folds into the end
    s += cyl_y(TUN_Y0 - DIVIDER - 0.5, YC - 6.0, WIRE_X_IN, WIRE_Z, WIRE_D)   # - wire
    s += lock_cuts()
    s += wire_groove()
    # hinge pin hole: closed at the bottom, open at the top of the wall - the filament pin drops
    # in from above before the keyboard plate goes on (the plate then covers it)
    s += cyl_z(HX, HY, PIN_Z0, PIN_Z1, DOOR_PIN + 0.15)
    return s


def strip_adds():
    """The fixed hinge knuckles, left standing inside the recess."""
    s = None
    for z0, z1 in CASE_KNUCKLES:
        k = cyl_z(HX, HY, z0, z1, 2 * KR) + box(HX, HY - 0.9, z0, HX + KR + 0.5, HY + 0.9, z1)
        k += box(0.0, HY - KR - 0.4, z0, HX + KR + 0.4, HY, z1)          # joined to the wall: no gap
        s = k if s is None else s + k
    s += lock_rail()
    return s - cyl_z(HX, HY, PIN_Z0, PIN_Z1, DOOR_PIN + 0.15)


def outline_prism(z0=-1.0, z1=40.0):
    import cover
    return cover.prism(cover.outline(), z0, z1)


def base_strip():
    return (strip_solid() - strip_cuts() + strip_adds()) & outline_prism()


def door():
    """Built closed, in place."""
    d = box(0.1, DOOR_Y0, FLOOR + CLR, DOOR_T, REC_Y1 - CLR, REC_Z1 - CLR)          # panel
    d += box(0.1, HY, DOOR_KNUCKLE[0], HX, DOOR_Y0 + 0.5, DOOR_KNUCKLE[1])          # knuckle web
    d += cyl_z(HX, HY, *DOOR_KNUCKLE, 2 * KR)
    d -= cyl_z(HX, HY, DOOR_KNUCKLE[0] - 1, DOOR_KNUCKLE[1] + 1, DOOR_PIN + 0.35)
    d -= box(DOOR_SLOT_X0, YC - SLOT_HALF_W, SLOT_Z0,                               # - plate slot,
             DOOR_SLOT_X0 + PLATE_SLOT, YC + SLOT_HALF_W, REC_Z1)                  # open at the top
    d -= cyl_x(DOOR_SLOT_X0, DOOR_T + 1, YC, ZC, 12.0)                              # spring window
    d -= cyl_x(DOOR_SLOT_X0, DOOR_T + 1, YC - 5.0, ZC + 6.7, 1.6)                   # - wire hole
    d += box(TAB[0], REC_Y1 - CLR - 0.01, LOCK_Z - TAB[2] / 2, DOOR_T,               # lock tab
             REC_Y1 + TAB[1], LOCK_Z + TAB[2] / 2)
    return d & outline_prism()                     # outer face follows the case's rounded corner


def swung(part, deg):
    """The door opened by deg (its back edge swings out)."""
    return Pos(HX, HY, 0) * Rot(0, 0, deg) * Pos(-HX, -HY, 0) * part


if __name__ == "__main__":
    import os
    os.makedirs("out", exist_ok=True)
    strip, dr = base_strip(), door()
    print(f"chamber d{BORE}, cell space {NEG_X:.1f}..{SHOULDER_X:.1f}, strip length {END_X:.1f}")
    print("strip valid", strip.is_valid, "door valid", dr.is_valid)
    print("door vs strip overlap (should be 0):", round((strip & dr).volume, 3))
    export_stl(strip, "out/battery_strip_test.stl")
    lk = door_lock()
    print("lock valid", lk.is_valid, "lock vs strip", round((strip & lk).volume, 3), "vs door", round((dr & lk).volume, 3),
          "unlocked vs strip", round((strip & door_lock(LOCK_TRAVEL)).volume, 3))
    export_stl(lk, "out/_lock_inplace.stl")
    export_stl(Pos(0, 0, 0) * Rot(0, -90, 0) * lk, "out/battery_lock_slider.stl")
    # printed standing up as installed: the - contact slot then opens upward (printed flat its roof is
    # an unsupported 17 mm bridge that sags shut). Use a brim - it is tall and thin.
    export_stl(Pos(0, 0, -dr.bounding_box().min.Z) * dr, "out/battery_door.stl")
    export_step(strip + dr, "out/battery_test_assembly.step")
