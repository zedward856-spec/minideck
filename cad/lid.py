"""Screen lid: front bezel (screen window) screws into the back shell (hinge, driver board):
4 x M2 countersunk screws through the bezel into heat-set inserts in bosses in the shell.

Built in the CLOSED position, screen facing down onto the keyboard.
Hinge: one long barrel across the back of the lid, hidden between the base box's end cheeks.
Cables (HDMI ribbon + 5 V pair + GPS coax) come up cheek B, through the hollow axle tube, along the
barrel's bore and into the lid between x 60 and 68.

    python3 lid.py   -> out/screen_front.stl, out/screen_back.stl
"""
import _here  # noqa: F401  (repo root as the working dir)
from build123d import Axis, Cone, Pos, Rot, fillet, export_stl, export_step
from params import *
import cover
from battery_test import box, cyl_x, cyl_z
from base import (M2_CLEAR, M2_CSK, M2_PILOT, CEN, HINGE_AXIS, HINGE_R, BARREL, CABLE_BORE, AXLE_OD, AXLE_IN, LID_CABLE_X, LID_TOP_Z,
                  TORQUE, TQ_CAP, BEND_R,
                  lid_profile, yz_prism, outline_prism)

LZ0 = TOP_Z + LID_GAP                   # bezel stands clear of the proud keys; the shell's
                                        # walls come down to TOP_Z and rest on the plate's border
LWALL = 2.0
BEZEL_T = 1.2
PANEL_Z = LZ0 + BEZEL_T
DRIVER_Z = PANEL_Z + PANEL_T + 0.5
TOP_T = 1.5
LID_TOP = DRIVER_Z + DRIVER_T + 0.3 + TOP_T
assert abs(LID_TOP - LID_TOP_Z) < 1e-6
IN = (LWALL, LWALL, OUT_W - LWALL, OUT_D - LWALL)      # x0, y0, x1, y1 inside the shell

# panel (landscape); its VIEWING area is centred on the lid (the panel itself sits 2.2 mm right,
# because the active area is off-centre towards its non-FPC end). FPC comes off the right edge.
PANEL_X0 = OUT_W / 2 - ACTIVE_W / 2 - ACTIVE_OFF[0]
PANEL_Y0 = (IN[1] + IN[3]) / 2 - ACTIVE_H / 2 - ACTIVE_OFF[1]
ACT_X0, ACT_Y0 = PANEL_X0 + ACTIVE_OFF[0], PANEL_Y0 + ACTIVE_OFF[1]
DRIVER_X0 = OUT_W / 2 - DRIVER_W / 2               # centred in the lid, behind the screen
DRIVER_Y0 = PANEL_Y0

# GPS patch antenna frame on the inside of the lid's back, left of the driver board
PATCH_X0 = IN[0] + 1.3
PATCH_Y0 = 30.0
PATCH_WALL, PATCH_CLR = 1.0, 0.2

# bezel screws: M2 countersunk through the bezel corners into M2x3x3.5 inserts in shell bosses
BEZEL_SCREWS = [(6.0, 5.0), (OUT_W - 6.0, 5.0), (6.0, OUT_D - 5.0), (OUT_W - 6.0, OUT_D - 5.0)]  # posts merge into the walls
BOSS_D = 6.5
REBATE = (0.8, 0.6, 0.1)                 # bezel lip: reach into the wall, thickness, seam gap
PAD_T = 1.0                              # bezel is thickened to 2.2 round each screw


def corner_guides(x0, y0, w, d, z0, z1, skip_side=0):
    """skip_side: -1 = no guides on the left corners, +1 = none on the right."""
    s = None
    gx0, gy0, gx1, gy1 = x0 - 0.3, y0 - 0.3, x0 + w + 0.3, y0 + d + 0.3
    for cx, cy, sx, sy in ((gx0, gy0, -1, -1), (gx1, gy0, 1, -1), (gx0, gy1, -1, 1), (gx1, gy1, 1, 1)):
        if sx == skip_side:
            continue
        a0, a1 = sorted((cx, cx + sx * 1.0))
        b0, b1 = sorted((cy - sy * 4, cy + sy * 1.0))
        c0, c1 = sorted((cx - sx * 4, cx + sx * 1.0))
        e0, e1 = sorted((cy, cy + sy * 1.0))
        g = box(max(a0, IN[0] - 0.1), max(b0, IN[1] - 0.1), z0, min(a1, IN[2] + 0.1), min(b1, IN[3] + 0.1), z1)
        g += box(max(c0, IN[0] - 0.1), max(e0, IN[1] - 0.1), z0, min(c1, IN[2] + 0.1), min(e1, IN[3] + 0.1), z1)
        s = g if s is None else s + g
    return s


def screen_front():
    e = CLR
    f = cover.prism(cover.outline().buffer(-(LWALL + e)), LZ0, PANEL_Z)
    # face lip: tucks into a rebate in the shell wall so the seam is a tight 0.1 mm step, not a slit
    f += cover.prism(cover.outline().buffer(-(LWALL - REBATE[0] + REBATE[2])), LZ0, LZ0 + REBATE[1])
    # window over the active area, with a stepped chamfer on the viewing side
    f -= box(ACT_X0 - 0.3, ACT_Y0 - 0.3, LZ0 - 1, ACT_X0 + ACTIVE_W + 0.3, ACT_Y0 + ACTIVE_H + 0.3, PANEL_Z + 1)
    f -= box(ACT_X0 - 1.1, ACT_Y0 - 1.1, LZ0 - 1, ACT_X0 + ACTIVE_W + 1.1, ACT_Y0 + ACTIVE_H + 1.1, LZ0 + 0.5)
    # frame that locates the panel; open on the right for the FPC
    fr = box(PANEL_X0 - 1.3, PANEL_Y0 - 1.3, PANEL_Z, PANEL_X0 + PANEL_W + 1.3, PANEL_Y0 + PANEL_H + 1.3,
             PANEL_Z + PANEL_T - 0.3)
    fr -= box(PANEL_X0 - 0.3, PANEL_Y0 - 0.3, PANEL_Z - 1, PANEL_X0 + PANEL_W + 0.3,
              PANEL_Y0 + PANEL_H + 0.3, PANEL_Z + PANEL_T + 1)
    fr -= box(PANEL_X0 + PANEL_W, PANEL_Y0 + PANEL_H / 2 - 12, PANEL_Z - 1, PANEL_X0 + PANEL_W + 2,
              PANEL_Y0 + PANEL_H / 2 + 12, PANEL_Z + PANEL_T + 1)
    f += fr
    bt_cut = bezel_text_cut()
    if bt_cut is not None:
        f -= bt_cut
    if BEZEL_LOGO.get("enabled", True):                          # logo under the screen
        from logo import logo_poly
        win_y1 = ACT_Y0 + ACTIVE_H + 1.1
        cy = (win_y1 + OUT_D - LWALL - CLR) / 2
        f -= cover.prism(logo_poly(BEZEL_LOGO["width"], OUT_W / 2, cy), LZ0 - 0.5, LZ0 + BEZEL_LOGO["depth"])
    for x, y in BEZEL_SCREWS:                                      # countersunk M2 holes
        f += cyl_z(x, y, PANEL_Z - 0.01, PANEL_Z + PAD_T, BOSS_D) & \
            cover.prism(cover.outline().buffer(-(LWALL + e)), PANEL_Z - 1, PANEL_Z + PAD_T + 1)
        f -= cyl_z(x, y, LZ0 - 1, PANEL_Z + PAD_T + 1, M2_CLEAR)
        f -= Pos(x, y, LZ0 - 0.01) * Cone(M2_CSK / 2 + 0.2, M2_CLEAR / 2, 1.0, align=CEN)
    return f


def lid_text_cut():
    """The engraved name, as a solid to cut from the lid's top face (see LID_TEXT in params.py)."""
    import os
    from build123d import Text, extrude, Align as A
    t = LID_TEXT
    if not t.get("enabled", True) or not t["text"]:
        return None
    font = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), t["font"])
    probe = Text(t["text"], font_size=10.0, font_path=font, align=(A.CENTER, A.CENTER))
    bb = probe.bounding_box()
    size = 10.0 * t["height"] / max(bb.size.Y, 1e-6)            # scale so the caps are `height` tall
    txt = Text(t["text"], font_size=size, font_path=font, align=(A.CENTER, A.CENTER))
    x = OUT_W / 2 if t["x"] is None else t["x"]
    cut = Rot(0, 0, t["angle"]) * extrude(txt, t["depth"] + 0.5)
    if t.get("face", "top") == "front":          # stood up on the front face, cut in towards +y
        z = (TOP_Z + LID_TOP) / 2 if t.get("z") is None else t["z"]
        return Pos(x, t["depth"], z) * Rot(90, 0, 0) * cut
    return Pos(x, t["y"], LID_TOP - t["depth"]) * cut


def bezel_text_cut():
    """Name engraved into the bezel face under the screen (see BEZEL_TEXT in params.py). With the
    lid open the hinge edge is at the bottom, so the letters' 'up' points to the front edge (-y)."""
    import os
    from build123d import Text, extrude, Align as A
    t = BEZEL_TEXT
    if not t.get("enabled", True) or not t["text"]:
        return None
    font = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), t["font"])
    bb = Text(t["text"], font_size=10.0, font_path=font, align=(A.CENTER, A.CENTER)).bounding_box()
    size = 10.0 * t["height"] / max(bb.size.Y, 1e-6)
    txt = Text(t["text"], font_size=size, font_path=font, align=(A.CENTER, A.CENTER))
    win_y1 = ACT_Y0 + ACTIVE_H + 1.1                       # back edge of the window's chamfer
    strip_y1 = OUT_D - LWALL - CLR
    x = OUT_W / 2 if t["x"] is None else t["x"]
    y = (win_y1 + strip_y1) / 2 if t["y"] is None else t["y"]
    return Pos(x, y, LZ0 + t["depth"]) * Rot(180, 0, 0) * extrude(txt, t["depth"] + 0.5)


def logo_polygons():
    """The LOGO placed on the lid back (x, y)."""
    from logo import logo_poly
    t = LOGO
    cx = OUT_W / 2 if t["x"] is None else t["x"]
    cy = (IN[1] + IN[3]) / 2 if t["y"] is None else t["y"]
    return logo_poly(t["width"], cx, cy, t["angle"], flip_v=False)


def lid_logo_cut():
    if not LOGO.get("enabled", True):
        return None
    return cover.prism(logo_polygons(), LID_TOP - LOGO["depth"], LID_TOP + 0.5)


def screen_back():
    s = outline_prism(TOP_Z, LID_TOP)
    s -= cover.prism(cover.outline().buffer(-LWALL), TOP_Z - 1, LID_TOP - TOP_T)
    s -= cover.prism(cover.outline().buffer(-(LWALL - REBATE[0])), TOP_Z - 1, LZ0 + REBATE[1] + 0.1)  # rebate
    for x, y in BEZEL_SCREWS:                                      # bosses for the bezel screws
        z0 = PANEL_Z + PAD_T + 0.05
        s += cyl_z(x, y, z0, LID_TOP - TOP_T + 0.01, BOSS_D) & \
            cover.prism(cover.outline().buffer(-0.5), PANEL_Z, LID_TOP)
        s -= cyl_z(x, y, z0 - 0.1, z0 + M2_INSERT["l"] + 0.4, M2_INSERT["hole"])
        s -= cyl_z(x, y, z0, z0 + M2_INSERT["l"] + 1.6, M2_PILOT)
    # GPS patch antenna frame (ceramic face up against the lid back = towards the sky)
    w = GPS_PATCH[0] + 2 * PATCH_CLR
    top_in = LID_TOP - TOP_T
    fx0, fy0 = PATCH_X0, PATCH_Y0
    s += box(fx0 - PATCH_WALL, fy0 - PATCH_WALL, top_in - 2.5, fx0 + w + PATCH_WALL, fy0 + w + PATCH_WALL, top_in + 0.01)
    s -= box(fx0, fy0, top_in - 3.0, fx0 + w, fy0 + w, top_in + 0.005)
    s -= box(fx0 + w / 2 - 2.0, fy0 + w - 0.1, top_in - 3.0, fx0 + w / 2 + 2.0, fy0 + w + PATCH_WALL + 0.1,
             top_in + 0.005)                              # notch for the u.FL lead, towards the hinge
    # hinge: one long barrel across the back, flush with the lid's top, hidden between the cheeks
    hy, hz = HINGE_AXIS
    from shapely.geometry import box as sbox
    s += yz_prism(lid_profile(True).intersection(sbox(OUT_D - 0.5, 0, 200, LID_TOP + 1)), *BARREL)
    over = lid_profile(False).intersection(sbox(OUT_D - 0.5, 0, 200, LID_TOP + 1))     # over the cheeks
    s += yz_prism(over, 0.0, BARREL[0]) + yz_prism(over, BARREL[1], OUT_W)
    # left end: clearance round the torque hinge's body, then a D-socket for its shaft
    t = TORQUE
    body_end = TQ_CAP[1] + t["body_l"]
    s -= cyl_x(BARREL[0] - 0.1, body_end + 0.4, hy, hz, t["body_d"] + 0.8)
    sock = cyl_x(body_end + 0.3, body_end + t["shaft_l"] + 0.5, hy, hz, t["shaft_d"] + 0.15)
    sock &= box(0, hy - 9, hz - 9, OUT_W, hy + 9, hz + t["shaft_flat"] - t["shaft_d"] / 2 + 0.075)
    s -= sock
    # right end: the axle tube turns in it; the cables run along the bore and up into the lid
    s -= cyl_x(BARREL[1] - AXLE_IN - 0.4, BARREL[1] + 0.1, hy, hz, AXLE_OD + 0.3)
    s -= cyl_x(LID_CABLE_X[0] - 1.0, BARREL[1], hy, hz, CABLE_BORE)
    cz0 = max(hz - CABLE_BORE / 2, PANEL_Z + 0.3)       # channel floor kept above the bezel: hidden
    s -= box(LID_CABLE_X[0], IN[3] - 0.5, cz0, LID_CABLE_X[1], hy, hz + CABLE_BORE / 2)
    # round the edge the cables bend round as they turn from the bore into the lid
    r, x, y = BEND_R, LID_CABLE_X[1], hy - CABLE_BORE / 2
    s -= box(x - 0.01, y - r, cz0, x + r, y + 0.01, hz + CABLE_BORE / 2) - \
        cyl_z(x + r, y - r, hz - CABLE_BORE, hz + CABLE_BORE, 2 * r)
    tc = lid_text_cut()
    if tc is not None:
        s -= tc
    lc = lid_logo_cut()
    if lc is not None:
        s -= lc
    import marks                                  # hex texture round the logo (marks.py)
    mc = marks.lid_cut()
    if mc is not None:
        s -= mc
    import stripes
    sc = stripes.stripes_cut("lid")
    if sc is not None:
        s -= sc
    return s


if __name__ == "__main__":
    import os
    os.makedirs("out", exist_ok=True)
    f, b = screen_front(), screen_back()
    print(f"lid {LID_TOP - LZ0:.1f} thick -> closed deck {LID_TOP:.1f} mm")
    print(f"active area centre {ACT_X0 + ACTIVE_W / 2:.2f}, {ACT_Y0 + ACTIVE_H / 2:.2f} "
          f"(lid centre {OUT_W / 2:.2f}, {(IN[1] + IN[3]) / 2:.2f})")
    print(f"panel at x {PANEL_X0:.1f}-{PANEL_X0 + PANEL_W:.1f}, y {PANEL_Y0:.1f}-{PANEL_Y0 + PANEL_H:.1f}")
    if LOGO.get("enabled", True):
        print("logo bounds on the lid back", [round(v, 1) for v in logo_polygons().bounds])
    bc = bezel_text_cut()
    if bc is not None:
        bb = bc.bounding_box()
        print(f"bezel text x {bb.min.X:.1f}-{bb.max.X:.1f}, y {bb.min.Y:.1f}-{bb.max.Y:.1f}, z {bb.min.Z:.2f}-{bb.max.Z:.2f}")
    tc = lid_text_cut()
    if tc is not None:
        bb = tc.bounding_box()
        print(f"text '{LID_TEXT['text']}' on the {LID_TEXT['face']} face: x {bb.min.X:.1f}-{bb.max.X:.1f}, "
              f"y {bb.min.Y:.1f}-{bb.max.Y:.1f}, z {bb.min.Z:.1f}-{bb.max.Z:.1f}, {LID_TEXT['depth']} mm deep")
    print("front valid", f.is_valid, "back valid", b.is_valid, "overlap", round((f & b).volume, 3))
    export_stl(Pos(0, 0, -LZ0) * f, "out/screen_front.stl")                          # face down
    export_stl(Pos(0, 0, LID_TOP) * Rot(180, 0, 0) * b, "out/screen_back.stl")       # top down
    export_stl(f, "out/_front_inplace.stl")
    export_stl(b, "out/_back_inplace.stl")
    export_step(f + b, "out/lid_assembly.step")
