"""Minideck case - built around the user's own part placement in minideck.stl.

Case frame: X = left -> right, Y = front -> back (hinge side), Z = up.
Origin = outside front-left-bottom corner. minideck.stl coords map in with MD_OFFSET.
"""
import _here  # noqa: F401  (repo root as the working dir)

# minideck.stl -> case frame (case outline = the user's keyboard cover, centred on the keyboard
# exactly as the cover sits over the keyboard copy in minideck.stl)
MD_OFFSET = (85.17, -11.94, 1.2)

# ---- print fit -------------------------------------------------------------
CLR = 0.2

# ---- shell -----------------------------------------------------------------
WALL = 2.0          # left / right / back
FRONT_WALL = 1.6
FLOOR = 1.2
OUT_W, OUT_D = 93.73, 64.09              # = the cover's outline

KB_TURN = 180                            # keyboard (and its cover) turned 180 deg from minideck.stl
GROVE_REMOVED = True                     # Grove connector desoldered: no window in the cover plate

# ---- heights (from the user's placement) ------------------------------------
RADXA_TOP_PARTS = 2.3                    # the real Radxa's microSD/eMMC side faces up when flipped
KB_Z = 19.23 + MD_OFFSET[2] + RADXA_TOP_PARTS   # keyboard (with its silicone cover) bottom
CV_Z0 = KB_Z                             # the cover's rim sits on the case walls here
# keys stand proud of the cover plate, and stay at or above it when pressed:
SILICONE_H = 5.3                         # CardKB + silicone cover, board bottom -> key tops (listed)
PLATE_UNDER = 3.18                       # plate underside above the board, as in HarukiToreda's case
KEY_PROUD = 0.75                         # keys above the plate at rest (> key travel)
KB_PLATE_T = SILICONE_H - KEY_PROUD - PLATE_UNDER   # 1.37: the cover's plate, 0.28 taken off its top
TOP_Z = KB_Z + PLATE_UNDER + KB_PLATE_T  # top of the keyboard plate
LID_GAP = KEY_PROUD + 0.3                # the screen lid stands this far above the plate, on its walls

# ---- 18650 chamber: where the user put the battery (y, z), slid left for the door spring ----
CELL_D = 18.55
CELL_L = 70.0                            # protected high-drain cells (Nitecore NL1835HP 69.3, Keeppower 3500 68.9) + clearance
CELL_BUTTON = 1.0
BORE = 18.9                              # round chamber; the keyboard is its roof
CH_YC = 60.3 + MD_OFFSET[1]
CH_ZC = 9.77 + MD_OFFSET[2]
TUN = BORE + 0.5
TUN_Y0 = CH_YC - TUN / 2
DIVIDER = 1.2

# ---- battery contacts ---------------------------------------------------------
PLATE_W, PLATE_H, PLATE_T = 16.5, 16.0, 0.3
PLATE_SLOT = 0.7
SPRING_SPACE = 5.0
BLOCKER_T = 0.8
BLOCKER_HOLE = 7.0
BACKWALL_T = 1.2

# ---- hinged battery door ------------------------------------------------------
DOOR_T = 2.2
DOOR_PIN = 1.75
DOOR_KNUCKLE_R = 1.6

# ---- screen (EP28060S 2.8" non-touch, landscape) + HDMI driver board ---------
# from the seller's EP28060S drawing (images/Se4116d2f4b7.png): outline 47.80 x 66.95,
# active 43.20 x 57.60, 2.43 from the top edge (FPC is on the other end), 2.30 from the side.
# 3.56 total is the touch version; the user has the NON-touch panel (no touch glass, ~2.0).
PANEL_W, PANEL_H, PANEL_T = 66.95, 47.8, 2.1
ACTIVE_W, ACTIVE_H = 57.6, 43.2
ACTIVE_OFF = (2.43, 2.30)                # from the panel's left (non-FPC) end, from its bottom edge
# EHD-40P-V3, from the seller's own photo with dimensions (screen_kit_images/img11.jpg):
# 47.928 x 48.457 mm (no touch board: non-touch panel). The 47.93 edge carries the mini-HDMI
# and USB-C; it faces the hinge. The touch connector is desoldered, so the tallest part is the
# mini-HDMI: 0.6 under the board + 1.6 PCB + 3.4 mini-HDMI/USB-C = 5.6 mm.
DRIVER_BOARD = (47.93, 48.46)
DRIVER_W, DRIVER_D, DRIVER_T = DRIVER_BOARD[0], DRIVER_BOARD[1], 5.6
C2_HEAD_DEPTH = 5.0                      # C2 (mini-HDMI 90 deg) end stands behind the board's port

# ---- GPS: module in the free bay right of the battery, ceramic patch antenna in the lid --------
# (the bay is under the keyboard, which would shade a GPS antenna; the patch goes in the lid,
#  joined to the module by a 1.13 mm u.FL coax that runs through the hollow hinge)
GPS_MODULE = (15.6, 16.4, 4.5)           # max module size: length, width, height incl. parts (mini ATGM336H ~13x15)
# the GPS stands on its long edge against the battery chamber's end wall (parts + u.FL face the right wall),
# so the longer chamber for a protected cell fits; cables still run along the right wall past it
GPS_EDGE = dict(gap=0.4, lip=(0.7, 2.0), stop=(1.2, 8.0))
GPS_PATCH = (18.0, 18.0, 4.5)            # 18x18 patch fits; a 15x15 one sits centred on foam tape

# ---- M2 heat-set inserts (brass, knurled; pushed in with a soldering iron) ----------------
M2_INSERT = dict(od=3.5, hole=3.2, l=3.0)        # M2 x 3 x 3.5: plate corners, hatch
M2_INSERT_LONG = dict(od=3.5, hole=3.2, l=4.0)   # M2 x 4 x 3.5: battery-door lock (its post)

# ---- radios in the box under the hinge (adhesive FPC antennas + SDR) ----------------------
# x0, y0, z0, x1, y1, z1 in the case frame. FPC antennas stick to the box walls with their tape.
ANT_LORA = (12.0, 79.79, 12.0, 50.0, 79.89, 22.0)    # Molex 211140-0100, 868/915 MHz FPC: 38 x 10 x 0.1
ANT_SDR = (11.0, 79.59, 1.6, 81.0, 79.89, 11.6)      # slot for an SDR FPC up to ~70 x 10 (pick by band)
ANT_WIFI = (48.0, 70.5, 22.73, 82.9, 79.5, 22.93)    # Molex 146153-0100, 2.4/5 GHz FPC: 34.9 x 9, under the roof
SDR_BODY = (14.0, 67.5, 1.55, 38.0, 75.5, 22.55)     # NESDR Nano 2+: 24 x 21 x 8, stood on its edge, lifted
# it stands on two thin ribs on the hatch (air under it instead of its whole 24 x 8 face on the floor, which
# sits on the desk), between four locating posts; 0.38 mm of air stays above it under the compartment roof
# the hatch's edge is stepped: a thin outer flange tucks under a ledge in the case all round (no straight gap to see
# through or for dust; the screws pull it up against the ledge), plus a low stiffening rim along its long edges inside
HATCH_STEP = dict(flange=0.6, overlap=0.8, rim_t=1.0, rim_h=1.6, rim_x=(10.6, 83.1))   # rims >= 2 lines
SDR_REST = dict(lift=0.35, rib_w=1.2, rib_in=1.5, post=(1.2, 1.0, 2.0), end=(1.2, 2.4, 2.0), clr=0.25)   # >= 2 lines thick
SDR_USB = (38.0, 67.75, 6.5, 50.0, 72.25, 18.5)      # (unused: plug cut off, wired to header pins 27/28)
SDR_ADAPTER = (50.0, 66.5, 5.5, 68.0, 73.5, 19.5)    # (unused)

# ---- engraved name on the screen lid's top (outside when closed), by the front edge ------
# Change any of these and re-run  python3 lid.py && python3 check.py
LID_TEXT = dict(
    face="front",                   # "front" = the lid's front face (faces you when closed), "top"
    text="MINIDECK",
    font="models/CorptaDEMO.otf",   # Corpta (demo) - any .ttf/.otf path works
    height=5.0,                     # cap height, mm (font size is scaled to hit this)
    depth=0.6,                      # engraving depth, mm (front wall 2.0, top 1.5 thick)
    x=None,                         # centre x; None = centred on the lid
    y=7.0,                          # face="top" only: centre y from the front edge
    z=None,                         # face="front" only: centre height; None = middle of the face
    angle=0.0,                      # rotation in degrees (0 = reads from the front)
    enabled=True,                   # False = no text
)

# ---- engraved hazard stripes (from the NZXT H710i Cyberpunk reference) --------------------
# Base: a band all the way round (skips the battery door + lock on the left).
# Lid: both sides full length, and on the front from each corner in to the MINIDECK text.
# Same 45 deg slant everywhere; on the front/back faces the two halves are mirrored so the
# pattern reads continuously round the corners. Change and re-run
#   python3 base.py && python3 lid.py && python3 check.py
SIDE_STRIPES = dict(
    enabled=True,
    depth=0.6,                      # groove depth (walls are 1.6-2.0 thick)
    bar=2.2,                        # bar width, measured along the face
    gap=2.0,                        # gap between bars
    slant=45.0,                     # bar angle from vertical
    corner_r=1.5,                   # rounded ends of each band
    tip_r=0.25,                     # slight rounding of the bars' sharp corners
    edge=5.0,                       # bands stop this far from each rounded case corner
    text_gap=3.0,                   # lid front: gap left either side of the MINIDECK text
    hole_gap=2.0,                   # base: stripes stay this far from every hole / recess / door
    shallow_over_switch=True,       # left face: bars run over the knob pocket's 0.7 mm skin, cut only switch_depth there
    switch_depth=0.2,
    switch_gap=0.6,                 # ... and keep this far from the fin slot
    bottom=dict(z0=2.5, z1=21.0),   # base band height (covers the port area); add bar=/gap= here
                                    # to give the base its own (e.g. fatter) bars
    lid=dict(z0=30.4, z1=36.4),     # lid band height
    segments=None,                  # None = automatic layout above; or a list of
                                    # (part, face, u0, u1, lean) - part "bottom"/"lid", face
                                    # "left"/"right"/"front"/"back", u along the face (y on the
                                    # sides, x on front/back), lean +1/-1
)

# ---- engraved name on the screen bezel, under the screen (reads upright with the lid open) ---
BEZEL_TEXT = dict(                   # (replaced by the logo - see BEZEL_LOGO)
    text="MINIDECK",
    font="models/CorptaDEMO.otf",
    height=3.5,                     # cap height, mm (the strip under the screen is ~7 mm)
    depth=0.5,                      # engraving depth (bezel is 1.2 thick)
    x=None,                         # centre x; None = centred
    y=None,                         # centre y; None = middle of the strip below the screen window
    enabled=False,
)

# ---- your logo (zedward "optic"), engraved on the back of the screen lid ---------------------
LOGO = dict(
    file="models/optic_logo.svg",   # simple SVG (M/L/Z paths), filled shapes are engraved
    width=40.0,                     # logo width on the lid, mm (height follows its proportions)
    depth=0.6,                      # engraving depth (lid top is 1.5 thick)
    x=None, y=None,                 # centre; None = centre of the lid's back
    angle=0.0,                      # rotation, degrees
    enabled=True,
)

# ---- more logos (same svg as LOGO). Each: width mm, engraving depth mm, enabled -------------
BEZEL_LOGO = dict(width=9.5, depth=0.5, enabled=True)        # under the screen, centred in the strip
PLATE_LOGO = dict(width=13.0, depth=0.4, x=8.8, y=45.5, enabled=True)   # keyboard plate, top left
HINGE_LOGO = dict(width=9.0, depth=0.3, enabled=True)        # both hinge end caps (always upright)

# ---- microSD: the socket is at the board's LEFT end (Radxa drawing: TF on the bottom side, the 22-pin
# camera FPC at the right end). No opening in the case: take the keyboard plate off to swap the card.
SD_CARD = dict(y=(12.4, 23.4), z=(20.42, 21.17), mouth_x=26.5, protrude=2.0)   # inserted card, case frame

# ---- power switch: a common SS12D00 mini slide switch (SPDT) in the TP4056 OUT+ wire. Its body sits against
# the inside of the left wall, beside the charger (only its pins and solder joints reach over the charger). The
# printed knob goes in FROM THE INSIDE: its plate lives in a pocket on the wall's inner side and is far bigger
# than the outside slot, so it can never come out of the case; only its thin vertical fin shows, flush with the
# outside face. The switch body behind it keeps it in. Set to your switch:
SWITCH = dict(body=(8.6, 3.5, 3.6),      # along the slide (y), lever axis (x), across (z)
              lever=(1.5, 1.3, 0.6),     # lever: along slide, across, length out of the body AFTER trimming (0.6: leaves a
                                         # solid 0.6 mm backbone in the knob behind its socket, under the fin)
              travel=2.0,                # lever travel end to end
              pins=(3, 2.54, 3.5, 0.5),  # count, pitch, length, size
              y=20.0, top=22.5,          # body centre (y) and top (under the keyboard at 22.73)
              face_x=2.0,                # body face (lever side): against the wall's inside, over the knob pocket
              skin=0.7,                  # outer skin of the wall the fin passes through (fin top flush with it)
              knob=(12.0, 3.4, 1.2),     # knob plate (inside the wall): length (y), height (z), thickness
              fin=(1.2, 3.0),            # thin vertical fin: width (y), height (z)
              clr=0.15)                  # clearances

# ---- NFC mark on the underside, right under the PN532 (nfc_mark.py): board outline, antenna coil, NFC + specs
NFC_MARK = dict(depth=0.3,                 # floor under the PN532 is 0.8 mm: 0.5 mm stays
                line=0.55, pitch=1.25,     # line width (>= nozzle) and coil turn pitch
                inset=0.6, coil_gap=2.2, turns=4,
                nfc_h=6.5,
                lines=[("13.56 MHz", 3.6), ("ISO 14443 A/B", 3.2), ("TAP HERE", 3.2)],
                close=0.2)                 # small text: gaps under 0.4 mm merged (a 0.4 nozzle can't print them)

# ---- 5 V boost: Pololu U3V40F5 (fixed 5 V, ~2.6 A out from 3.7 V in, 15.2 x 15.2 x 5.6 mm), lying flat in the old
# MT3608 spot under the charger. Fed from the TP4056's B+/B- pads (battery side, past its ~3 A protection) through
# the power switch; a protected high-drain 18650 does the over-current protection. Pads along its back edge.
BOOST = dict(model="Pololu U3V40F5", size=(15.2, 15.2, 5.6), x0=5.0, y0=19.0, z0=9.0, pcb=1.6)

# ---- cosmetic engravings (marks.py): port labels, switch I/O, lock arrow, underside plates, lid texture ----
MARKS = dict(
    enabled=True,
    depth=0.3,                      # engraving depth (painted like the logos, except the lid texture)
    wall=0.45,                      # at least this much wall stays behind every mark (else it's clipped)
    stripe_gap=0.6,                 # stripes keep this far from the left-face marks
    front=dict(z=23.3, h=2.4),      # port labels PWR PWR DATA (+ headphones): centre height (above the stripes) and cap height
    switch=dict(h=2.6, line=0.55, gap=0.8, depth=0.2, round=0.18),   # | (on, knob back) left of the slot, O (off) right, seen from outside; 0.2 deep (0.7 skin)
    lock=dict(h=4.2, w=2.6, gap=1.1, up=0.0),  # "open" arrow behind the battery lock (slide up to open)
    battery=dict(y=53.6, h=13.0, line=0.6, inset=1.5, text_h=2.6),   # outline under the cell
    plates=dict(w=20.4, h=37.5, line=0.55, title_h=3.4, text_h=2.6, label_h=1.9, gap=1.3,
                name="sl01220", id_xy=(79.51, 23.2), rf_xy=(14.2, 23.2)),   # either side of the NFC mark, 1.7 mm off it (clear of the door pin)
    texture=dict(enabled=True, cell=5.0, line=0.6, depth=0.25, edge=3.2, back=4.0, logo_gap=2.5, screw_gap=3.0, border=0.6),
)
