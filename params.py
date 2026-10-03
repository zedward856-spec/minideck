"""Minideck case - built around the user's own part placement in minideck.stl.

Case frame: X = left -> right, Y = front -> back (hinge side), Z = up.
Origin = outside front-left-bottom corner. minideck.stl coords map in with MD_OFFSET.
"""

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
CELL_L = 67.2
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
GPS_MODULE = (15.6, 16.4, 4.5)           # max module size x, y, height (mini ATGM336H boards ~13x15)
GPS_PATCH = (18.0, 18.0, 4.5)            # 18x18 patch fits; a 15x15 one sits centred on foam tape

# ---- M2 heat-set inserts (brass, knurled; pushed in with a soldering iron) ----------------
M2_INSERT = dict(od=3.5, hole=3.2, l=3.0)        # M2 x 3 x 3.5: plate corners, hatch
M2_INSERT_LONG = dict(od=3.5, hole=3.2, l=4.0)   # M2 x 4 x 3.5: battery-door lock (its post)

# ---- radios in the box under the hinge (adhesive FPC antennas + SDR) ----------------------
# x0, y0, z0, x1, y1, z1 in the case frame. FPC antennas stick to the box walls with their tape.
ANT_LORA = (12.0, 79.79, 12.0, 50.0, 79.89, 22.0)    # Molex 211140-0100, 868/915 MHz FPC: 38 x 10 x 0.1
ANT_SDR = (11.0, 79.59, 1.6, 81.0, 79.89, 11.6)      # slot for an SDR FPC up to ~70 x 10 (pick by band)
ANT_WIFI = (48.0, 70.5, 22.73, 82.9, 79.5, 22.93)    # Molex 146153-0100, 2.4/5 GHz FPC: 34.9 x 9, under the roof
SDR_BODY = (14.0, 66.0, 1.3, 38.0, 74.0, 22.3)       # NESDR Nano 2+: 24 x 21 x 8, stood on its edge
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
