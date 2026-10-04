"""Paint-fill previews for the engravings (logos, MINIDECK text, side stripes): solids that sit
exactly inside each recess, flush with the surface - shown coloured in the viewer.

    python3 fills.py -> out/parts_in_place/fill_{logos,caps,stripes}_{base,lid}.stl
"""
from build123d import Pos, Rot, extrude, Text, Align as A, export_stl
from params import *
import base as B, lid as Ld, cover, stripes
from logo import logo_poly

E = 0.04                                   # fill stops this far under the surface (no z-fighting)

def logos_lid():
    out = []
    if LOGO.get("enabled", True):          # lid back
        out.append(cover.prism(Ld.logo_polygons(), Ld.LID_TOP - LOGO["depth"], Ld.LID_TOP - E))
    if BEZEL_LOGO.get("enabled", True):    # bezel, under the screen
        win_y1 = Ld.ACT_Y0 + ACTIVE_H + 1.1
        cy = (win_y1 + OUT_D - Ld.LWALL - CLR) / 2
        out.append(cover.prism(logo_poly(BEZEL_LOGO["width"], OUT_W / 2, cy), Ld.LZ0 + E, Ld.LZ0 + BEZEL_LOGO["depth"]))
    t = LID_TEXT                           # MINIDECK on the lid front
    if t.get("enabled", True) and t.get("face") == "front":
        import os
        font = os.path.join(os.path.dirname(os.path.abspath(__file__)), t["font"])
        bb = Text(t["text"], font_size=10.0, font_path=font, align=(A.CENTER, A.CENTER)).bounding_box()
        size = 10.0 * t["height"] / max(bb.size.Y, 1e-6)
        txt = Text(t["text"], font_size=size, font_path=font, align=(A.CENTER, A.CENTER))
        x = OUT_W / 2 if t["x"] is None else t["x"]
        z = (TOP_Z + Ld.LID_TOP) / 2 if t.get("z") is None else t["z"]
        out.append(Pos(x, t["depth"], z) * Rot(90, 0, 0) * extrude(Rot(0, 0, t["angle"]) * txt, t["depth"] - E))
    return out

def logos_base():
    if not PLATE_LOGO.get("enabled", True):
        return []
    lp = logo_poly(PLATE_LOGO["width"], PLATE_LOGO["x"], PLATE_LOGO["y"])
    return [cover.prism(lp, B.TOP_Z - PLATE_LOGO["depth"], B.TOP_Z - E)]

def caps():
    if not HINGE_LOGO.get("enabled", True):
        return []
    hy, hz = B.HINGE_AXIS
    poly = logo_poly(HINGE_LOGO["width"], hy, hz)
    d = HINGE_LOGO["depth"]
    return [B.yz_prism(poly, 0.05 + E, 0.05 + d), B.yz_prism(poly, OUT_W - d, OUT_W - E)]

def stripe_fill(part):
    s = SIDE_STRIPES
    if not s.get("enabled", True):
        return []
    d, z0, z1, out = s["depth"], s[part]["z0"], s[part]["z1"], []
    for prt, face, u0, u1, lean in stripes.segments():
        if prt != part or u1 - u0 < 3:
            continue
        poly = stripes.patch_polygon(u0, u1, z0, z1, lean, stripes.keepouts(part, face), part)
        if poly.is_empty:
            continue
        if face == "left":
            out.append(B.yz_prism(poly, E, d))
        elif face == "right":
            out.append(B.yz_prism(poly, OUT_W - d, OUT_W - E))
        elif face == "front":
            out.append(stripes._xz_prism(poly, E, d))
        else:
            out.append(stripes._xz_prism(poly, B.BOX_BACK - d, B.BOX_BACK - E))
    return out

def save(solids, name):
    solids = [s for s in solids if s is not None]
    if not solids:
        return
    u = solids[0]
    for s in solids[1:]:
        u = u + s
    export_stl(u, f"out/parts_in_place/{name}.stl")
    print("wrote", name)

def nfc_fill():
    """paint fill for the NFC mark under the PN532 (underside: from just inside the face up to its depth)"""
    import nfc_mark
    return [nfc_mark.solid(E, NFC_MARK["depth"])]

if __name__ == "__main__":
    save(logos_lid(), "fill_logos_lid")
    save(logos_base(), "fill_logos_base")
    save(caps(), "fill_caps_base")
    save(stripe_fill("lid"), "fill_stripes_lid")
    save(stripe_fill("bottom"), "fill_stripes_base")
    save(nfc_fill(), "fill_nfc_base")
