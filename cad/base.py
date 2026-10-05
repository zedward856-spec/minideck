"""Bottom piece, built around the user's placement (layout.py).

The walls rise around the keyboard so it sits inside the case; the top plate of the user's
'Keyboard Cover.stl' (flipped front-to-back so its key openings match) goes on top and is
screwed down at the four corners.

    python3 base.py   -> out/bottom.stl, out/keyboard_top.stl, out/base_assembly.step
"""
import _here  # noqa: F401  (repo root as the working dir)
import math
import numpy as np
import trimesh
import manifold3d as mf
from shapely.geometry import box as sbox
from build123d import (Align, Axis, Box, Cone, Pos, Rot, fillet, Plane, Polyline, make_face, extrude,
                       export_stl, export_step)
from params import *
import layout as L
import battery_test as bt
import cover
from battery_test import box, cyl_x, cyl_y, cyl_z

CEN = (Align.CENTER, Align.CENTER, Align.MIN)
IN_X0, IN_X1, IN_Y0, IN_Y1 = WALL, OUT_W - WALL, FRONT_WALL, OUT_D - WALL

WALL_TOP = TOP_Z - KB_PLATE_T            # walls rise to the plate
SEAT_Z = WALL_TOP
KB_POCKET_CLR = 0.2
CLAMP_T = 0.0                            # no rim: the plate's underside rests on the silicone itself
PLATE_SCREWS = [(3.2, 3.3), (OUT_W - 3.2, 3.3), (3.2, OUT_D - 3.3), (OUT_W - 3.2, OUT_D - 3.3)]
M2_PILOT, M2_CLEAR, M2_CSK = 1.7, 2.3, 4.0

PEG_D, PEG_H = 2.4, 1.3                  # pegs through the Radxa's holes (short: it must slide in under the front ledge, then drop on)
GPS_Y0 = 38.6                            # GPS module cradle: front edge of the module
USB_SLOT_CLR, USB_RECESS = 0.3, (11.8, 6.5, 0.8)
JACK_HOLE, JACK_RECESS = 5.4, (8.0, 0.8)   # hugs the jack barrel, recess for the plug body
HDMI_SKIN = 1.2                          # front wall left in front of the (internal) micro-HDMI
                                         # (1.2 so the 0.6 mm stripe grooves can cross it)

# hidden hinge: a box grows out of the back of the base. Its two end cheeks (A left, B right)
# hide the ends of one long barrel that belongs to the lid; the barrel's top is flush with the
# closed lid, so from the side the deck is a box with one rounded back-top edge.
#   left:  a torque (friction) hinge: its body sits in cheek A, its D-shaft in the barrel end, so
#          the screen stays where you leave it; a flush printed cap hides it
#   right: hollow axle tube (separate part, pushed in from the right) through cheek B into the
#          barrel; the screen cables + GPS coax run lid -> barrel bore -> tube -> down cheek B
#          -> the box's compartment -> through the old back wall into the base
LID_TOP_Z = TOP_Z + LID_GAP + 1.2 + PANEL_T + 0.5 + DRIVER_T + 0.3 + 1.5   # = lid.LID_TOP
HINGE_R = 7.5                            # barrel radius (= cheek radius)
HINGE_AXIS = (OUT_D + 0.4 + HINGE_R, LID_TOP_Z - HINGE_R)
HINGE_CLR = 0.4
MAX_OPEN = 180                           # the box's back is cut round so the lid opens flat
CHEEK_A = (0.0, 10.5)                    # same as cheek B: symmetric
CHEEK_B = (OUT_W - 10.5, OUT_W)
BARREL = (CHEEK_A[1] + HINGE_CLR, CHEEK_B[0] - HINGE_CLR)
# torque hinge (cylinder type with a D-shaft). Set these to the one you buy:
TORQUE = dict(body_d=8.0, body_l=16.0, shaft_d=5.0, shaft_flat=4.0, shaft_l=8.0)
TQ_CAP = (11.0, 1.2)                     # flush cap over it in cheek A: dia, thickness
BOX_WALL = 1.6
BOX_BACK = HINGE_AXIS[0] + HINGE_R + HINGE_CLR + BOX_WALL
CMP_TOP = HINGE_AXIS[1] - HINGE_R - HINGE_CLR - 1.2      # antenna compartment roof (under the trough)
HATCH_CLR = 0.2
HATCH = (4.0, OUT_D + 1.2, OUT_W - 4.0, BOX_BACK - 3.0)  # screwed hatch in the box floor
HATCH_SCREWS = [(HATCH[0] + 3.0, HATCH[1] + 3.0), (HATCH[2] - 3.0, HATCH[1] + 3.0),
                (HATCH[0] + 3.0, HATCH[3] - 3.0), (HATCH[2] - 3.0, HATCH[3] - 3.0)]
CABLE_BORE = 8.4                         # cables pass through this (roll the HDMI ribbon)
AXLE_OD, AXLE_IN = 10.8, 4.3             # hollow axle tube, and how far it reaches into the barrel
AXLE_FLANGE = (13.0, 1.4)                # D-shaped flange (dia, thick), sits flush in cheek B
AXLE_FLAT = 5.2                          # flange's flat, above the axis (keys it: window faces down)
CHEEK_EASE = 0.8                         # inside-corner rounding behind each cheek
OVER_BACK = 4.2                          # the lid's lip over the cheeks stops this far before the axis
NECK_BACK = 3.2                          # cheek neck reaches this far behind the axis (lid clears it)
CHEEK_B_CHANNEL_Y = (-4.5, NECK_BACK - 0.8)   # cable drop in cheek B, y from the axis (walled in)
BEND_R = 3.0                             # cable bends are rounded at least this much
CHEEK_B_CHANNEL = (CHEEK_B[0] + 1.3, OUT_W - AXLE_FLANGE[1] - 1.5)   # cables drop down cheek B here
BASE_CABLE_X = (78.5, 86.5)              # where the cables leave the base into the box
BAY_OPEN = (76.6, 90.0, FLOOR + 1.3, 21.0)  # big opening, bay right of the battery -> box compartment
                                         # (screen cables, antenna coax, SDR USB all pass here)
LID_CABLE_X = (60.0, 68.0)               # where they come out of the barrel into the lid


def lid_profile(mid):
    """Side view (y, z) of the closed lid near the hinge; mid = the part between the cheeks."""
    from shapely.geometry import Point
    from shapely.ops import unary_union
    hy, hz = HINGE_AXIS
    full = sbox(OUT_D - 40, TOP_Z, OUT_D, LID_TOP_Z)
    disk = Point(hy, hz).buffer(HINGE_R, 128)
    hull = unary_union([full, disk]).convex_hull.intersection(sbox(0, TOP_Z, 200, 100))
    if mid:
        return hull.union(disk)
    # over the cheeks the lid reaches back too (no gap at the top), clear of the cheek's round
    over = hull.difference(Point(hy, hz).buffer(HINGE_R + HINGE_CLR, 128)).intersection(
        sbox(0, 0, hy - OVER_BACK, 200))                 # its knife-thin back tip trimmed off
    return unary_union([full, over])


def swept(poly, a0=0, a1=MAX_OPEN, grow=HINGE_CLR):
    """Everything the lid profile passes through while opening from a0 to a1 degrees."""
    from shapely import affinity
    from shapely.ops import unary_union
    hy, hz = HINGE_AXIS
    s = unary_union([affinity.rotate(poly, -a, origin=(hy, hz)) for a in np.arange(a0, a1 + 0.5, 1.0)])
    return s.buffer(grow).simplify(0.03)


def yz_prism(poly, x0, x1):
    """Extrude a side-view (y, z) polygon along x."""
    out = None
    for g in (poly.geoms if hasattr(poly, "geoms") else [poly]):
        if g.area < 0.05:
            continue
        f = make_face(Polyline(*list(g.exterior.coords)[:-1], close=True))
        s = extrude(Plane.YZ.offset(x0) * f, x1 - x0)
        out = s if out is None else out + s
    return out


def axle():
    """Hollow axle tube: pushed in from the right through cheek B into the barrel (press fit,
    a drop of glue if loose). The cables come along its bore and drop out of its window."""
    hy, hz = HINGE_AXIS
    x0 = BARREL[1] - AXLE_IN
    t = cyl_x(x0, OUT_W - AXLE_FLANGE[1], hy, hz, AXLE_OD)
    fl = cyl_x(OUT_W - AXLE_FLANGE[1], OUT_W, hy, hz, AXLE_FLANGE[0])
    fl -= box(OUT_W - 2, hy - 9, hz + AXLE_FLAT, OUT_W + 1, hy + 9, hz + 9)            # D flat on top
    t += fl
    t -= cyl_x(x0 - 1, OUT_W - 2.4, hy, hz, CABLE_BORE)                                # bore, closed end
    t -= box(CHEEK_B_CHANNEL[0], hy - CABLE_BORE / 2, hz - AXLE_OD, CHEEK_B_CHANNEL[1],
             hy + CABLE_BORE / 2, hz)                                                   # window, down
    lc = hinge_logo_cut(OUT_W, -1)
    if lc is not None:
        t -= lc
    return t


def bend_round_b():
    """Rounds the edge the cables bend over where they drop out of the bore into cheek B."""
    hy, hz = HINGE_AXIS
    r, x, z = BEND_R, CHEEK_B_CHANNEL[0], hz - CABLE_BORE / 2
    return box(x - r, hy + CHEEK_B_CHANNEL_Y[0], z - r, x + 0.01, hy + CHEEK_B_CHANNEL_Y[1], z + 0.01) - \
        cyl_y(hy - CABLE_BORE, hy + CABLE_BORE, x - r, z - r, 2 * r)


BOX_TOP = HINGE_AXIS[1] - HINGE_R - HINGE_CLR   # flat box top: the lid clears it all the way to 180 deg
BOX_EDGE_R = 2.0                               # rounded back-top edge (blends into the R4 corners)


def box_shell():
    """The box behind the base: flat top, R4 vertical back corners, rounded back-top edge."""
    from build123d import Box as B3Box, Align as A
    y0 = OUT_D - 6.0
    blk = Pos(0, y0, 0) * B3Box(OUT_W, BOX_BACK - y0, BOX_TOP, align=(A.MIN, A.MIN, A.MIN))
    blk = fillet(blk.edges().filter_by(Axis.Z).filter_by(lambda e: e.center().Y > BOX_BACK - 0.1), 4.0)
    top_back = [e for e in blk.edges() if abs(e.center().Z - BOX_TOP) < 1e-3
                and min(v.Y for v in e.vertices()) > BOX_BACK - 4.2]
    blk = fillet(top_back, BOX_EDGE_R)
    return blk & box(-1, OUT_D, -1, OUT_W + 1, BOX_BACK + 1, BOX_TOP + 1)


def hinge_fill(back_deg, bottom=None):
    """Side view of the base filled in round the hinge: flush up to just under the plate level in
    front of the axis (the lid never dips below that there), and behind it down along a line
    back_deg below horizontal (the lid's lip only passes low behind that line, at 180 deg)."""
    from shapely.geometry import Polygon
    hy, hz = HINGE_AXIS
    T, Bz = TOP_Z, (BOX_TOP - 0.5 if bottom is None else bottom)   # top flush: the lid rests on it
    k = math.tan(math.radians(back_deg))
    return Polygon([(OUT_D, Bz), (OUT_D, T), (hy + (hz - T) / k, T), (hy + (hz - Bz) / k, Bz)])


def cheek_profile():
    """Side view of an end cheek: the round end grows out of the filled-in base."""
    from shapely.geometry import Point
    hy, hz = HINGE_AXIS
    return hinge_fill(64.0).union(Point(hy, hz).buffer(HINGE_R, 128))


def cheek_ease():
    """Rounded inside corners behind a cheek (slope -> round end, slope -> box top), as the extra
    material sitting on top of the box only, so it never meets the box's rounded edges."""
    hy, hz = HINGE_AXIS
    p = cheek_profile()
    top = sbox(hy, BOX_TOP - 0.5, BOX_BACK, BOX_TOP)
    eased = p.union(top).buffer(CHEEK_EASE, 64).buffer(-CHEEK_EASE, 64).difference(p)
    yb = hy + (hz - BOX_TOP) / math.tan(math.radians(64.0))
    return eased.intersection(sbox(hy + 0.5, BOX_TOP - 0.01, yb + 2 * CHEEK_EASE, hz))


def mid_profile():
    """Side view of the base under the hinge bar: filled, with a 0.4 mm gap round the bar."""
    from shapely.geometry import Point
    hy, hz = HINGE_AXIS
    return hinge_fill(75.0).difference(Point(hy, hz).buffer(HINGE_R + HINGE_CLR, 128))


def hinge_logo_cut(x_face, inward):
    """Logo on a hinge end face (x = x_face), cut `inward` (+1/-1 in x); upright = +z."""
    if not HINGE_LOGO.get("enabled", True):
        return None
    from logo import logo_poly
    hy, hz = HINGE_AXIS
    poly = logo_poly(HINGE_LOGO["width"], hy, hz)                 # (y, z) on the face
    d = HINGE_LOGO["depth"]
    x0, x1 = (x_face - 0.5, x_face + d) if inward > 0 else (x_face - d, x_face + 0.5)
    return yz_prism(poly, x0, x1)


def torque_cap():
    hy, hz = HINGE_AXIS
    c = cyl_x(0.05, TQ_CAP[1], hy, hz, TQ_CAP[0] - 0.15)
    lc = hinge_logo_cut(0.05, +1)
    return c - lc if lc is not None else c


def outline_prism(z0, z1):
    return cover.prism(cover.outline(), z0, z1)


def kb_outline(grow=0.0):
    """The keyboard body's outline (the outward grooves near its base are ignored), grown by `grow`."""
    kb = L.meshes()["keyboard"]
    s = kb.section(plane_origin=[0, 0, KB_Z + 2.5], plane_normal=[0, 0, 1])
    p, _ = s.to_2D(to_2D=np.eye(4))
    return max(p.polygons_full, key=lambda g: g.area).convex_hull.buffer(grow)


def hatch():
    """Floor hatch of the antenna compartment (4 x M2 from below, countersunk)."""
    e, st = HATCH_CLR, HATCH_STEP
    f, ov = st["flange"], st["overlap"]
    h = box(HATCH[0] + e, HATCH[1] + e, 0, HATCH[2] - e, HATCH[3] - e, f)                     # outer flange
    h += box(HATCH[0] + ov + e, HATCH[1] + ov + e, f - 0.01, HATCH[2] - ov - e, HATCH[3] - ov - e, FLOOR)
    y0, y1 = HATCH[1] + ov + e, HATCH[3] - ov - e                                            # stiffening rims
    for ya, yb in ((y0, y0 + st["rim_t"]), (y1 - st["rim_t"], y1)):
        h += box(st["rim_x"][0], ya, FLOOR - 0.01, st["rim_x"][1], yb, FLOOR + st["rim_h"])
    for x, y in HATCH_SCREWS:
        h -= cyl_z(x, y, -1, FLOOR + 1, M2_CLEAR)
        h -= Pos(x, y, -0.01) * Cone(M2_CSK / 2, M2_CLEAR / 2, 0.9, align=CEN)
    h += sdr_rest()
    return h


def sdr_rest():
    """Two thin ribs the SDR stands on (air under the rest of it) + posts that keep it in place."""
    r, (x0, y0, _, x1, y1, _) = SDR_REST, SDR_BODY
    top, c = FLOOR + r["lift"], r["clr"]
    pw, pd, ph = r["post"]
    ew, ed, eh = r["end"]
    out = None
    for xa in (x0 + r["rib_in"], x1 - r["rib_in"] - r["rib_w"]):
        rib = box(xa, y0 + 0.5, FLOOR - 0.01, xa + r["rib_w"], y1 - 0.5, top)
        rib += box(xa, y0 - c - pd, FLOOR - 0.01, xa + pw, y0 - c, FLOOR + ph)      # front post
        rib += box(xa, y1 + c, FLOOR - 0.01, xa + pw, y1 + c + pd, FLOOR + ph)      # back post
        out = rib if out is None else out + rib
    ym = (y0 + y1) / 2
    out += box(x0 - c - ew, ym - ed / 2, FLOOR - 0.01, x0 - c, ym + ed / 2, FLOOR + eh)   # end stops
    out += box(x1 + c, ym - ed / 2, FLOOR - 0.01, x1 + c + ew, ym + ed / 2, FLOOR + eh)
    return out


def grow(b, d):
    return (b[0] - d, b[1] - d, b[2] - d, b[3] + d, b[4] + d, b[5] + d)


def port_slot(xc, zc, w, h, r=1.4):
    return Pos(xc, -1, zc) * Rot(-90, 0, 0) * fillet(
        Box(w, h, FRONT_WALL + 1.3, align=CEN).edges().filter_by(Axis.Z), r)


def port_recess(xc, zc, w, h, d):
    return Pos(xc, -1, zc) * Rot(-90, 0, 0) * fillet(
        Box(w, h, d + 1, align=CEN).edges().filter_by(Axis.Z), min(3.0, h / 2 - 0.1))


def bottom():
    B = {n: L.bounds(n) for n in L.meshes()}
    b = outline_prism(0, WALL_TOP)
    inner = box(IN_X0, IN_Y0, FLOOR, IN_X1, IN_Y1, KB_Z)
    b -= fillet(inner.edges().filter_by(Axis.Z), 2.0)
    b -= cover.prism(kb_outline(KB_POCKET_CLR), KB_Z, WALL_TOP + 1)      # the keyboard's pocket
    b += bt.strip_solid()

    # ledge the keyboard rests on, clear of the boards below
    kb = B["keyboard"]
    ring = cover.outline().buffer(-1.9).difference(sbox(kb[0] + 2.5, kb[1] + 2.5, kb[3] - 2.5, kb[4] - 2.5))
    ledge = cover.prism(ring, KB_Z - 1.0, KB_Z)
    for n in ("tp4056", "mt3608", "radxa", "dac"):
        ledge -= box(*grow(B[n], 0.3))
    # notch above the GPS spot so the module drops straight in (keyboard is held either side)
    ledge -= box(bt.END_X, GPS_Y0 - 1.5, KB_Z - 2, OUT_W, GPS_Y0 + GPS_MODULE[1] + 1.5, KB_Z + 1)
    b += ledge
    for x, y in PLATE_SCREWS:                                           # the plate's screws
        # plain self-tapping M2 (no room for a heat-set insert: the keyboard pocket is ~2 mm away)
        b -= cyl_z(x, y, WALL_TOP - 3.0, WALL_TOP + 1, M2_PILOT)           # (M2 x 4 screws)

    # the charger / boost compartment: just a wall between it and the right stack
    rb = B["radxa"]
    pcb_under = rb[5] - 1.2
    b += box(22.8, IN_Y0, FLOOR, 23.6, bt.TUN_Y0 - DIVIDER, pcb_under)
    for z0 in (3.0, 11.0):                                              # wire pass-throughs
        b -= box(22.7, 12.0, z0, 23.7, 19.0, z0 + 3.5)

    # Radxa (upside down): pegs through its four holes (right pillars from the floor, left
    # supports off the dividing wall). The keyboard above stops it lifting off the pegs.
    for x, y in L.radxa_holes():
        if x > 50:
            b += cyl_z(x, y, FLOOR, pcb_under, 5.0)
        else:                                   # boss on an arm off the dividing wall, 45 deg underneath
            zb = pcb_under - 2.5
            b += cyl_z(x, y, zb, pcb_under, 5.0)
            b += box(23.6, y - 2.5, zb, x, y + 2.5, pcb_under)
            run = x + 2.5 - 23.6
            gus = make_face(Polyline((23.6, zb - run), (23.6, zb + 0.01), (x + 2.5, zb + 0.01), close=True))
            b += extrude(Plane.XZ.offset(-(y + 2.5)) * gus, 5.0)
        b += cyl_z(x, y, pcb_under - 0.1, pcb_under + PEG_H, PEG_D)

    # DAC: front edge on a ledge off the front wall; its back rests on the LoRa (foam tape)
    dac = B["dac"]
    b += box(dac[0] + 1, IN_Y0, dac[2] - 0.6, dac[3] - 1, dac[1] + 1.8, dac[2])
    # PN532 on the floor, held by corner clips
    pn = B["pn532"]
    for cx, cy, sx, sy in ((pn[0], pn[1], -1, -1), (pn[3], pn[1], 1, -1), (pn[0], pn[4], -1, 1), (pn[3], pn[4], 1, 1)):
        px0, px1 = sorted((cx + sx * 0.25, cx + sx * 1.45))
        py0, py1 = sorted((cy - sy * 3, cy + sy * 1.2))
        b += box(px0, max(py0, IN_Y0), FLOOR, px1, py1, FLOOR + 3.1)
        lx0, lx1 = sorted((cx + sx * 0.25, cx - sx * 0.6))
        b += box(lx0, max(py0, IN_Y0), FLOOR + 2.3, lx1, py1, FLOOR + 3.1)

    # GPS module in the bay right of the battery, standing on its long edge with its back against the
    # chamber's end wall (foam tape): tall stops front/back and a low lip so its bottom edge can't slide out
    gy0, gy1 = GPS_Y0, GPS_Y0 + GPS_MODULE[1]
    ge = GPS_EDGE; gx1 = bt.END_X + ge["gap"] + GPS_MODULE[2]
    for y0, y1 in ((gy0 - ge["stop"][0], gy0), (gy1, gy1 + ge["stop"][0])):
        b += box(bt.END_X - 0.01, y0, FLOOR - 0.01, gx1 + ge["lip"][0], y1, FLOOR + ge["stop"][1])
    b += box(gx1, gy0, FLOOR - 0.01, gx1 + ge["lip"][0], gy1, FLOOR + ge["lip"][1])

    # front face: the wall hugs each port - a port-sized slot with a shallow plug recess
    ports, rp = L.port_cutouts(), L.radxa_ports()
    ux0, ux1, uz0, uz1, _ = ports["charger_usbc"]
    usb = [((ux0 + ux1) / 2, (uz0 + uz1) / 2, ux1 - ux0, uz1 - uz0)]
    for k in ("usbc_a", "usbc_b"):
        x0, x1 = rp[k]
        usb.append(((x0 + x1) / 2, sum(rp["z"]) / 2, x1 - x0, rp["z"][1] - rp["z"][0]))
    for xc, zc, w, h in usb:
        b -= port_slot(xc, zc, w + 2 * USB_SLOT_CLR, h + 2 * USB_SLOT_CLR)
    b -= port_recess(usb[0][0], usb[0][1], *USB_RECESS)              # charger
    (xa, za, _, _), (xb, zb, _, _) = usb[1], usb[2]                  # the Radxa's two ports share one recess (the
    b -= port_recess((xa + xb) / 2, (za + zb) / 2, xb - xa + USB_RECESS[0], *USB_RECESS[1:])   # web between was 0.66 mm)
    jx, jz, _ = ports["jack"]
    b -= cyl_y(-1, IN_Y0 + 0.1, jx, jz, JACK_HOLE)
    b -= cyl_y(-1, JACK_RECESS[1], jx, jz, JACK_RECESS[0])
    # micro-HDMI stays inside: no hole, but the wall is thinned in front of it for the most room
    hx0, hx1 = rp["hdmi"]
    b -= box(hx0 - 1.0, HDMI_SKIN, rp["z"][0] - 1.0, hx1 + 1.0, IN_Y0 + 0.1, rp["z"][1] + 1.0)
    # no microSD opening: the socket is at the board's LEFT end, deep inside; swap the card with the
    # keyboard plate off (the right end has the camera FPC, so both side walls stay closed)
    # power switch in the left wall, beside the charger: block + end stops under it, body pocket,
    # lever slot and the knob's recess outside (switch.py)
    import switch
    b += switch.case_adds()
    b -= switch.case_cuts()


    b &= outline_prism(-1, TOP_Z + 10)                   # nothing sticks outside the cover's outline

    # ---- the box behind: hides the hinge, holds the antennas --------------------------------
    hy, hz = HINGE_AXIS
    foot = sbox(0, OUT_D - 10, OUT_W, BOX_BACK).buffer(-4).buffer(4).intersection(
        sbox(0, OUT_D, OUT_W, BOX_BACK))
    bx = box_shell()
    for x0, x1 in (CHEEK_A, CHEEK_B):                                   # the end cheeks
        bx += yz_prism(cheek_profile(), x0, x1) & cover.prism(foot, -1, LID_TOP_Z + 1)
    bx += yz_prism(mid_profile(), CHEEK_A[1] - 0.01, CHEEK_B[0] + 0.01)   # filled in under the bar
    # the box's rounded top edge also runs along both sides; under the cheeks fill it back in so
    # each side is one flat face up to the cheek (the rounding only shows behind the cheek)
    side = hinge_fill(64.0, BOX_TOP - BOX_EDGE_R - 0.2).intersection(
        sbox(OUT_D, BOX_TOP - BOX_EDGE_R - 0.2, BOX_BACK, BOX_TOP + 0.01))
    for x0, x1 in ((0.0, 2.5), (OUT_W - 2.5, OUT_W)):          # (its end follows the cheek's slope)
        bx += yz_prism(side, x0, x1) & cover.prism(foot, -1, 40)
    # compartment (antennas etc.); open into the base only through the cable passage
    bx -= box(BOX_WALL, OUT_D + 1.2, FLOOR, OUT_W - BOX_WALL, BOX_BACK - BOX_WALL, CMP_TOP)
    bx -= box(4.0, OUT_D - 0.5, FLOOR, OUT_W - 4.0, OUT_D + 1.3, CMP_TOP)
    # solid backing for the battery-door lock's pocket where it reaches into the box
    bx += box(0.5, OUT_D - 0.5, bt.LOCK_ZB - 1.2, 9.0, bt.LOCK_REC_Y1 + 1.2,
              min(bt.LOCK_ZB + bt.LOCK_TRAVEL + bt.LOCK_BODY[1] + 1.2, CMP_TOP))
    # floor hatch: opening + 4 tabs above its edges for the M2 screws
    h0, h1 = HATCH[:2], HATCH[2:]
    ov = HATCH_STEP["overlap"]                       # stepped: the flange's recess, then the smaller opening above
    bx -= box(h0[0], h0[1], -1, h1[0], h1[1], HATCH_STEP["flange"])
    bx -= box(h0[0] + ov, h0[1] + ov, HATCH_STEP["flange"] - 0.01, h1[0] - ov, h1[1] - ov, FLOOR + 0.1)
    # two side rails from the front wall to the back wall (print as clean bridges), then the
    # insert holes - cut after all the rails are in, so no rail fills another's hole
    for xa, xb in ((BOX_WALL - 0.1, HATCH[0] + 6.0), (HATCH[2] - 6.0, OUT_W - BOX_WALL + 0.1)):
        bx += box(xa, OUT_D + 1.1, FLOOR, xb, BOX_BACK - BOX_WALL + 0.1, FLOOR + 4.4)
    for x, y in HATCH_SCREWS:
        bx -= cyl_z(x, y, FLOOR - 1, FLOOR + M2_INSERT["l"] + 0.4, M2_INSERT["hole"])
    # cheek A: pocket for the torque hinge's body, flush cap recess on the outside
    bx -= cyl_x(TQ_CAP[1] - 0.05, CHEEK_A[1] + 1, hy, hz, TORQUE["body_d"] + 0.1)
    bx -= cyl_x(-1, TQ_CAP[1], hy, hz, TQ_CAP[0])
    # cheek B: bore for the axle tube, flush D-flange pocket, M2 for the flange, cable drop
    bx -= cyl_x(CHEEK_B[0] - 1, OUT_W + 1, hy, hz, AXLE_OD + 0.15)
    fl = cyl_x(OUT_W - AXLE_FLANGE[1] - 0.1, OUT_W + 1, hy, hz, AXLE_FLANGE[0] + 0.3)
    fl -= box(OUT_W - 3, hy - 9, hz + AXLE_FLAT + 0.15, OUT_W + 2, hy + 9, hz + 9)
    bx -= fl
    bx -= bend_round_b()
    bx -= box(CHEEK_B_CHANNEL[0], hy + CHEEK_B_CHANNEL_Y[0], CMP_TOP - 0.5, CHEEK_B_CHANNEL[1],
              hy + CHEEK_B_CHANNEL_Y[1], hz)
    b += bx
    # cable passage: from the bay right of the battery through the old back wall into the box
    b -= box(BAY_OPEN[0], IN_Y1 - 0.5, BAY_OPEN[2], BAY_OPEN[1], OUT_D + 1.5, BAY_OPEN[3])
    b -= bt.strip_cuts()
    b += bt.strip_adds()
    # the PN532 sits in a 0.4 mm pocket in the floor (floor 0.8 mm under it)
    pn = L.bounds("pn532")
    if pn[2] < FLOOR - 0.01:
        b -= box(pn[0] - 0.3, pn[1] - 0.3, pn[2] - 0.01, pn[3] + 0.3, pn[4] + 0.3, FLOOR + 0.01)
    # the PN532 is longer than the gap between the front wall and the battery tube, so over its width the tube
    # is opened into a cradle (its front half removed down to the floor): the board drops straight in. The cell
    # is rigid and both its ends stay in closed tube, so it is still held; it sits 0.7 mm over the board's edge.
    b -= box(pn[0] - 0.25, pn[4] - 7.0, FLOOR, pn[3] + 0.25, bt.YC, bt.CV_Z0 + 0.01)
    import nfc_mark                                       # NFC mark engraved under the PN532 (underside)
    b -= nfc_mark.cut()
    import marks                                          # port labels, switch I/O, lock arrow, underside plates
    mc = marks.base_cut()
    if mc is not None:
        b -= mc
    import stripes
    sc = stripes.stripes_cut("bottom")
    if sc is not None:
        b -= sc
    return b


def _to_manifold(mesh):
    mesh = mesh.copy()
    mesh.merge_vertices()
    return mf.Manifold(mf.Mesh(vert_properties=np.asarray(mesh.vertices, np.float32),
                               tri_verts=np.asarray(mesh.faces, np.uint32)))


def _from_b3d(shape, tmp):
    export_stl(shape, tmp)
    return _to_manifold(trimesh.load(tmp))


def keyboard_top():
    """The user's cover, cut down to its top plate, with corner screw holes and a clamp rim."""
    # the cover's plate underside (4.34 above its rim) goes on the walls; 0.28 mm comes off its top
    cv = _to_manifold(cover.cover_in_case(WALL_TOP - 4.34))
    keep = mf.Manifold.cube([OUT_W + 20, OUT_D + 20, KB_PLATE_T + 0.01]).translate([-10, -10, WALL_TOP - 0.005])
    plate = cv ^ keep
    # the cover's back corners are rounded; square them off to match the case and the box behind
    # (a solid 1 mm band round the edge too: the cover's own edge is bevelled, which left a slit)
    corners = cover.outline().difference(cover.outline(rounded_back=True).buffer(-1.0))
    plate = plate + _from_b3d(cover.prism(corners, WALL_TOP, TOP_Z), "out/_corners.stl")
    # the keyboard's raised block over its chip sits in the cover's underside recess; with the
    # plate at its proper height the block reaches 0.18 mm past it, so deepen that recess a bit
    kb = L.meshes()["keyboard"]
    blk, top = None, None
    for z in np.arange(WALL_TOP + 0.05, TOP_Z, 0.05):          # slice up until the block ends
        s = kb.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
        pp, _ = s.to_2D(to_2D=np.eye(4))
        g = [q for q in pp.polygons_full if q.area > 60 and (q.bounds[2] - q.bounds[0]) < 20]
        if g:
            blk, top = g[0], z
        elif blk is not None:
            break
    if blk is not None:
        plate = plate - _from_b3d(cover.prism(blk.buffer(0.3), WALL_TOP - 1, top + 0.15), "out/_recess.stl")
    if GROVE_REMOVED:                                     # fill the cover's Grove window
        from shapely.geometry import box as sb
        win = cover.outline().buffer(-0.1).intersection(sb(0, 33.0, 14.6, 55.5))
        plate = plate + _from_b3d(cover.prism(win, WALL_TOP, TOP_Z), "out/_fill.stl")
    holes = None
    for x, y in PLATE_SCREWS:
        h = cyl_z(x, y, WALL_TOP - 1, TOP_Z + 1, M2_CLEAR)
        h += Pos(x, y, TOP_Z - 1.0) * Cylinder_csk()
        holes = h if holes is None else holes + h
    plate = plate - _from_b3d(holes, "out/_holes.stl")
    if PLATE_LOGO.get("enabled", True):          # logo, top left (last, after the Grove window fill)
        from logo import logo_poly
        lp = logo_poly(PLATE_LOGO["width"], PLATE_LOGO["x"], PLATE_LOGO["y"])
        plate = plate - _from_b3d(cover.prism(lp, TOP_Z - PLATE_LOGO["depth"], TOP_Z + 0.5), "out/_plate_logo.stl")
    out = plate.to_mesh()
    return trimesh.Trimesh(out.vert_properties[:, :3], out.tri_verts)


def Cylinder_csk():
    from build123d import Cone
    return Cone(M2_CLEAR / 2, M2_CSK / 2 + 0.3, 1.3, align=CEN)


if __name__ == "__main__":
    import os
    os.makedirs("out", exist_ok=True)
    bot = bottom()
    print(f"base {OUT_W:.2f} x {BOX_BACK:.2f} x {TOP_Z:.2f} mm (box {BOX_BACK - OUT_D:.1f} deep), "
          f"hinge axis y {HINGE_AXIS[0]:.2f} z {HINGE_AXIS[1]:.2f}, compartment z {FLOOR}-{CMP_TOP:.2f}")
    print("bottom valid", bot.is_valid, "vol", round(bot.volume))
    export_stl(bot, "out/bottom.stl", tolerance=0.005, angular_tolerance=0.05)
    _m = trimesh.load("out/bottom.stl"); _m.merge_vertices()
    if not _m.is_watertight:                       # close any meshing seams
        trimesh.repair.fill_holes(_m); _m.export("out/bottom.stl")
    export_stl(Pos(0, 0, 0) * hatch(), "out/box_hatch.stl")
    hy, hz = HINGE_AXIS
    ax = axle()
    print("axle valid", ax.is_valid, "hatch valid", hatch().is_valid)
    export_stl(ax, "out/_axle_inplace.stl")
    export_stl(Rot(0, 90, 0) * Pos(-OUT_W, -hy, -hz) * ax, "out/hinge_axle.stl")    # flange down
    export_stl(Rot(0, 90, 0) * Pos(0, -hy, -hz) * torque_cap(), "out/hinge_cap.stl")
    export_stl(torque_cap(), "out/_cap_inplace.stl")
    top = keyboard_top()
    print("keyboard top plate watertight", top.is_watertight, "bounds", top.bounds.round(2).tolist())
    top.export("out/_top_inplace.stl")
    flip = top.copy()
    flip.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0]))
    flip.apply_translation(-flip.bounds[0])
    flip.export("out/keyboard_top.stl")                     # print face-down
    export_step(bot, "out/base_assembly.step")
