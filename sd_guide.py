"""microSD guide sleeve: a separate printed part that runs from the card-sized slot in the left wall,
over the TP4056, to just before the Radxa's edge, so the card is steered into the socket at the board's
left end and nothing inside can be seen through the slot.

    python3 sd_guide.py   -> out/sd_guide.stl (print floor-down), out/parts_in_place/sd_guide.stl
"""
from build123d import Box, Pos, Align, export_stl
from params import *

A0 = (Align.MIN, Align.MIN, Align.MIN)
def box(x0, y0, z0, x1, y1, z1):
    return Pos(x0, y0, z0) * Box(x1 - x0, y1 - y0, z1 - z0, align=A0)

g = SD_GUIDE
cy0, cy1 = SD_CARD["y"]; cz0, cz1 = SD_CARD["z"]
ch = (cy0 - g["clr"], cz0 - g["clr"], cy1 + g["clr"], cz1 + g["clr"])            # channel y0 z0 y1 z1
OUTER = (ch[0] - g["side"], g["floor_z"], ch[2] + g["side"], g["top_z"])         # sleeve y0 z0 y1 z1

def sleeve():
    s = box(0.0, OUTER[0], OUTER[1], g["x1"], OUTER[2], OUTER[3])
    s += box(WALL, OUTER[0] - g["flange"], OUTER[1], WALL + g["flange_x"], OUTER[2] + g["flange"], OUTER[3])   # inside flange
    s -= box(-1, ch[0], ch[1], g["x1"] + 1, ch[2], ch[3])                            # card channel
    w, d = g["flare"]
    s -= box(-1, ch[0] - w, ch[1] - w * 0.6, d, ch[2] + w, ch[3] + w * 0.6)          # lead-in at the slot
    return s

def wall_cut():
    """the left-wall opening (sleeve + clearance) and the bit of keyboard ledge the sleeve passes under"""
    c = g["wall_clr"]
    cut = box(-1, OUTER[0] - c, OUTER[1] - c, WALL + 0.01, OUTER[2] + c, OUTER[3] + c)
    cut += box(WALL - 0.01, OUTER[0] - g["flange"] - c, OUTER[1] - c, 8.0, OUTER[2] + g["flange"] + c, 22.72)
    return cut

if __name__ == "__main__":
    s = sleeve()
    export_stl(s, "out/parts_in_place/sd_guide.stl")
    export_stl(Pos(0, -OUTER[0], -OUTER[1]) * s, "out/sd_guide.stl")               # floor on the bed
    bb = s.bounding_box()
    print("sd guide", round(bb.size.X, 2), "x", round(bb.size.Y, 2), "x", round(bb.size.Z, 2),
          "channel", round(ch[2] - ch[0], 2), "x", round(ch[3] - ch[1], 2), "floor", round(ch[1] - OUTER[1], 2),
          "ceiling", round(OUTER[3] - ch[3], 2))
