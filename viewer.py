"""Interactive 3D view of the whole deck with every part in place.

    python3 viewer.py
Left-drag rotate, right-drag/scroll zoom, middle-drag pan. Tick boxes show/hide parts;
the slider opens the screen lid.
"""
import os
import sys
# run on the RTX 3080 (this laptop otherwise renders OpenGL on the Intel iGPU)
_NV = {"__NV_PRIME_RENDER_OFFLOAD": "1", "__GLX_VENDOR_LIBRARY_NAME": "nvidia",
       "__VK_LAYER_NV_optimus": "NVIDIA_only"}
if any(os.environ.get(k) != val for k, val in _NV.items()) and "--no-nvidia" not in sys.argv:
    os.execve(sys.executable, [sys.executable] + sys.argv, {**os.environ, **_NV})
import numpy as np
import pyvista as pv
import trimesh

PARTS = [  # file, label, colour, start visible
    ("bottom", "case bottom", "#9aa7b0", True), ("keyboard_top", "keyboard plate (your cover)", "#4a4f55", True),
    ("battery_door", "battery door", "#e8741a", True), ("18650", "18650 cell", "#3060d0", True),
    ("keyboard", "keyboard", "#2a6e3f", True), ("radxa", "Radxa Zero 3W", "#2e8b57", True),
    ("pn532", "PN532", "#c0392b", True), ("dac", "DAC", "#d4ac0d", True), ("mt3608", "MT3608 boost", "#2471a3", True),
    ("tp4056", "TP4056 charger", "#1abc9c", True), ("lora", "LoRa", "#8e44ad", True),
    ("screen_front", "screen front", "#3a3f44", True), ("screen_back", "screen back", "#7d8b96", True),
    ("screen_panel", "screen panel", "#101830", True),
    ("driver_board", "EHD-40P-V3 driver board", "#1e50c8", True),
    ("gps_module", "GPS module", "#f0c828", True), ("gps_patch_antenna", "GPS patch antenna", "#e6e6dc", True),
    ("antenna_lora", "LoRa FPC antenna", "#e6c828", True), ("antenna_wifi", "Wi-Fi/BT FPC antenna", "#3cc8e6", True),
    ("antenna_sdr", "SDR FPC antenna", "#e678c8", True), ("sdr_dongle", "NESDR Nano 2+", "#1e1e1e", True),
    ("m2_hardware", "M2 inserts (hatch)", "#c8a03c", True), ("lid_inserts", "lid M2 inserts", "#c8a03c", True), ("torque_hinge", "torque hinge", "#282828", True), ("hinge_cap", "torque hinge cap", "#9aa7b0", True),
    ("hinge_axle", "hinge axle tube", "#c83c3c", True), ("door_lock", "battery door C-clip lock", "#f0c828", True), ("switch_knob", "power switch knob", "#f0c828", True), ("power_switch", "SS12D00 power switch", "#1a1a1c", True), ("box_hatch", "box floor hatch", "#6e7882", True),
]
WIRES = [("pwr", "wires: 5V / battery +", "#d62828"), ("gnd", "wires: GND", "#2b2b2b"),
         ("v33", "wires: 3.3V", "#f77f00"), ("i2c", "wires: I2C (CardKB, PN532)", "#277da1"),
         ("i2s", "wires: I2S (DAC)", "#43aa8b"), ("uart", "wires: UART (GPS, LoRa)", "#f9c74f"),
         ("gpio", "wires: GPIO (LoRa M0/M1/AUX, PN532 IRQ)", "#e8e8e8"), ("hdmi", "HDMI ribbon", "#c46b2c"),
         ("coax", "antenna coax", "#8d99ae"), ("usb", "wires: SDR USB (pins 27/28)", "#9d4edd")]
for _k, _lab, _c in WIRES:
    for _part in ("base", "lid"):
        if os.path.exists(f"out/parts_in_place/wires_{_part}_{_k}.stl"):
            PARTS.append((f"wires_{_part}_{_k}", _lab + (" (lid)" if _part == "lid" else ""), _c, True))
LID = {f for f, *_ in PARTS if f.startswith("wires_lid_")} | {"lid_inserts", "screen_front", "screen_back", "screen_panel", "driver_board", "gps_patch_antenna"}
import base as B
HY, HZ = B.HINGE_AXIS

OPACITY = 1.0                    # solid by default (finished look); the slider makes it see-through

SHOT = sys.argv[sys.argv.index("--shot") + 1] if "--shot" in sys.argv else None   # test render
p = pv.Plotter(window_size=(1500, 1000), title="Minideck - assembly with parts", off_screen=bool(SHOT))
p.enable_depth_peeling(number_of_peels=6)   # correct see-through layering (cheap on the 3080)
p.enable_anti_aliasing("ssaa")
p.enable_ssao(radius=4.0, bias=0.05, kernel_size=64, blur=True)   # soft contact shadows in corners
p.remove_all_lights()
p.enable_lightkit()                                                # key / fill / back / head lights
p.set_background("#d9dde2", top="#f7f8fa")
actors = {}
PARTS += [("screws_base", "M2 screws (plate, hatch)", "#c9cacc", True), ("screws_lid", "M2 screws (bezel)", "#c9cacc", True)]
LID.add("screws_lid")
# paint-filled engravings (python3 fills.py): yellow in the dark parts, dark in the yellow hinge caps
PARTS += [("fill_logos_base", "paint fill: plate logo", "#f7d116", True),
          ("fill_logos_lid", "paint fill: lid logos + MINIDECK", "#f7d116", True),
          ("fill_caps_base", "paint fill: hinge-cap logos (dark)", "#161616", True),
          ("fill_stripes_base", "paint fill: stripes (base)  [g]", "#f7d116", True),
          ("fill_stripes_lid", "paint fill: stripes (lid)  [g]", "#f7d116", True)]
LID |= {"fill_logos_lid", "fill_stripes_lid"}
PARTS = [p for p in PARTS if os.path.exists(f"out/parts_in_place/{p[0]}.stl")]   # skip parts not built

# ---- finished colours: what each part really looks like
# printed: Bambu PLA Matte Charcoal body, PLA Basic Grey plate/bezel, PLA Basic Yellow accents
CHARCOAL, GREY, YELLOW = "#2d2d2d", "#8b8e91", "#f7d116"      # neutral charcoal + warm "cyber yellow"
DARKGREY = "#3d3d3d"                                          # neutral dark grey: keyboard plate + bezel
# colour palettes for the printed parts + silicone keys; switch live with keys 1-6
PALETTES = {
    "1": dict(name="Cyber yellow", body=CHARCOAL, plate=GREY, kbplate=DARKGREY, accent=YELLOW, accent2=YELLOW,
              keys="#161616", ink="#f0f0f0", glow=0.0, bg=("#dcdcdc", "#f8f8f8")),
    "2": dict(name="Neon night", body="#0d0d12", plate="#22232c", accent="#05d9e8", accent2="#ff2a6d",
              keys="#161618", ink="#05d9e8", glow=0.55, bg=("#07070b", "#1a1030")),
    "3": dict(name="Arasaka", body="#111214", plate="#3b3d42", accent="#e0102a", accent2="#e0102a",
              keys="#161618", ink="#f0f0f0", glow=0.15, bg=("#1b1c20", "#3a3d44")),
    "4": dict(name="Snow", body="#e7e6e1", plate="#f6f6f3", accent="#ff5a10", accent2="#ff5a10",
              keys="#f2f2f0", ink="#202022", glow=0.0, bg=("#cfd3d8", "#ffffff")),
    "5": dict(name="Retro beige", body="#d6c9a8", plate="#bfb08c", accent="#7a1f2b", accent2="#7a1f2b",
              keys="#8e9093", ink="#f4f4f4", glow=0.0, bg=("#c9c3b4", "#f3efe6")),
    "6": dict(name="Field olive", body="#4b5320", plate="#b8a77c", accent="#1a1a1a", accent2="#1a1a1a",
              keys="#161618", ink="#e9e2c8", glow=0.0, bg=("#b9b7a6", "#e8e6da")),
}
PAL0 = os.environ.get("MINIDECK_PALETTE", "1")
COLOR = {
    "bottom": CHARCOAL, "screen_back": CHARCOAL, "box_hatch": CHARCOAL,
    "keyboard_top": DARKGREY, "screen_front": DARKGREY,
    "battery_door": YELLOW, "door_lock": YELLOW, "hinge_cap": YELLOW, "hinge_axle": YELLOW,
    # electronics, from the boards' real colours
    "radxa": "#2f9e57", "pn532": "#c62f2a", "dac": "#6b3fa6", "tp4056": "#1f4fa0", "mt3608": "#2468c4",
    "lora": "#b9bcc0", "gps_module": "#2b6e3c", "gps_patch_antenna": "#d8cdb3", "keyboard": "#ececec",
    "18650": "#22457a", "driver_board": "#1d4f9a", "screen_panel": "#0b0d12", "sdr_dongle": "#1a1a1a",
    "torque_hinge": "#56585c", "m2_hardware": "#b08d57", "lid_inserts": "#b08d57",
    "antenna_lora": "#c98a2b", "antenna_wifi": "#c98a2b", "antenna_sdr": "#c98a2b",
}
# (no reflection map here, so fully metallic surfaces render near-black: keep metals half-metallic)
METAL = {"screws_base": (0.55, 0.3), "screws_lid": (0.55, 0.3), "torque_hinge": (0.5, 0.4), "m2_hardware": (0.55, 0.35), "lid_inserts": (0.55, 0.35), "lora": (0.5, 0.35)}
PLASTIC_PRINT = {"bottom", "screen_back", "box_hatch", "keyboard_top", "screen_front", "battery_door",
                 "door_lock", "hinge_cap", "hinge_axle", "switch_knob",
                 "fill_logos_base", "fill_logos_lid", "fill_caps_base", "fill_stripes_base", "fill_stripes_lid"}
PARTS = [(f, l, COLOR.get(f, c), v) for f, l, c, v in PARTS]

def radxa_colours(m):
    """green PCB, black chips, silver ports / metal can - by where each face sits on the board."""
    import layout as _L
    _b = _L.bounds("radxa"); _rp = _L.radxa_ports()
    zp = (_rp["z"][0] + _rp["z"][1]) / 2 + 3.16 / 2
    c = m.cell_centers().points
    rgb = np.tile(np.array([47, 158, 87], np.uint8), (m.n_cells, 1))          # PCB
    off = (c[:, 2] < zp - 0.08) | (c[:, 2] > zp + 1.68)                        # parts on either side
    rgb[off] = (24, 24, 26)                                                     # chips
    metal = off & (((c[:, 1] < _b[1] + 7.5) & (c[:, 2] < zp - 0.08)) |          # USB-C / micro-HDMI
                   ((c[:, 0] > _b[3] - 6.0) & (c[:, 2] > zp + 1.68)))           # microSD socket
    rgb[metal] = (200, 202, 205)
    m.cell_data["rgb"] = rgb
    return m

def port_colours(f, m, board_rgb):
    """the charger's USB-C silver, the DAC's 3.5 mm jack black - the rest in the board colour."""
    import layout as _L
    pc = _L.port_cutouts()
    c = m.cell_centers().points
    rgb = np.tile(np.array(board_rgb, np.uint8), (m.n_cells, 1))
    if f == "tp4056":
        x0, x1, z0, z1, yf = pc["charger_usbc"]
        port = (c[:, 0] > x0 - 0.3) & (c[:, 0] < x1 + 0.3) & (c[:, 2] > z0 - 0.3) & (c[:, 2] < z1 + 0.3) & (c[:, 1] < yf + 7.6)
        rgb[port] = (200, 202, 205)
    else:
        jx, jz, yf = pc["jack"]
        port = (np.hypot(c[:, 0] - jx, c[:, 2] - jz) < 3.4) & (c[:, 1] < yf + 13.0)
        rgb[port] = (26, 26, 28)
    m.cell_data["rgb"] = rgb
    return m

def _hex(h):
    h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

# ---- the part list on the left: scrolls with the mouse wheel (over the list) when it outgrows the window
ROWS, ROW_H, _scroll = [], 21, [0]
PANEL_W = 300
def legend_row(cb, value, color, label):
    w = p.add_checkbox_button_widget(cb, value=value, position=(10, 0), size=18, color_on=color, color_off="#dddddd")
    t = p.add_text(label, position=(34, 1), font_size=8, color="black")
    ROWS.append((w, t))

def layout_rows():
    top = p.window_size[1] - 46                       # first row under the title area
    span = len(ROWS) * ROW_H - (top - 30)             # how far the list can scroll
    _scroll[0] = max(0, min(_scroll[0], max(span, 0)))
    for i, (w, t) in enumerate(ROWS):
        y = top - i * ROW_H + _scroll[0]
        show = 30 <= y <= top
        w.GetRepresentation().PlaceWidget([10, 28, y, y + 18, 0, 0])
        w.On() if show else w.Off()
        t.SetPosition(34, y + 1)
        t.SetVisibility(show)
    if _hint[0] is not None:
        _hint[0].SetVisibility(span > 0)
_hint = [None]

for i, (f, label, col, vis) in enumerate(PARTS):
    m = pv.read(f"out/parts_in_place/{f}.stl")
    met, rough = METAL.get(f, (0.05, 0.75 if f in PLASTIC_PRINT else 0.4))
    if f in ("tp4056", "dac"):
        m = port_colours(f, m, _hex(col))
        a = p.add_mesh(m, scalars="rgb", rgb=True, opacity=OPACITY, smooth_shading=True, split_sharp_edges=True,
                       feature_angle=35, pbr=True, metallic=0.1, roughness=0.45, diffuse=1.0)
    elif f == "radxa":
        m = radxa_colours(m)
        a = p.add_mesh(m, scalars="rgb", rgb=True, opacity=OPACITY, smooth_shading=True, split_sharp_edges=True,
                       feature_angle=35, pbr=True, metallic=0.1, roughness=0.4, diffuse=1.0)
    else:
        if f in PLASTIC_PRINT:                     # printed parts: classic shading, colours read true in any palette
            a = p.add_mesh(m, color=col, opacity=OPACITY, smooth_shading=True, split_sharp_edges=True,
                           feature_angle=35, ambient=0.35, diffuse=0.7, specular=0.15, specular_power=18)
        else:
            a = p.add_mesh(m, color=col, opacity=OPACITY, smooth_shading=True, split_sharp_edges=True,
                           feature_angle=35, pbr=True, metallic=met, roughness=rough, diffuse=1.0)
    a.SetVisibility(vis)
    actors[f] = a
    legend_row(lambda on, a=a: a.SetVisibility(on), vis, col, label)


# ---- the HarukiToreda silicone cover: black keys with the real white legends
try:
    import keycaps
    _caps, _rows, _arr = keycaps.build()
    _cap_actors, _cap_bodies, _cap_legends = [], [], []
    _pk = PALETTES[PAL0]
    for _mesh, _spec in _caps:
        if _spec is None:
            _a = p.add_mesh(_mesh, color=_pk["keys"], smooth_shading=True, ambient=0.3, diffuse=0.7, specular=0.05)
            _cap_bodies.append(_a)
        else:
            _a = p.add_mesh(_mesh, texture=keycaps.legend(*_spec, key=_pk["keys"], ink=_pk["ink"]),
                            ambient=0.35, diffuse=0.75, specular=0.05)
            _cap_legends.append((_a, _spec))
        _cap_actors.append(_a)
    _ky = 8 + len(PARTS) * 21 + 21
    def _caps_vis(on):
        for _a in _cap_actors: _a.SetVisibility(on)
    legend_row(_caps_vis, True, "#161618", "silicone keys (HarukiToreda, black)")
except Exception as _e:
    print("keycaps skipped:", _e)

# ---- what the screen shows: plays an animation (default: your Optic loading GIF) on the panel's
# active area, glowing, in the lid group so it swings with the lid
SCREEN_MEDIA = os.environ.get("MINIDECK_SCREEN", "models/optic-loading.gif")
screen_frames, screen_ms = [], 40
if os.path.exists(SCREEN_MEDIA):
    from PIL import Image, ImageSequence
    import lid as Ld
    from params import ACTIVE_W, ACTIVE_H
    _im = Image.open(SCREEN_MEDIA)
    screen_ms = int(_im.info.get("duration", 40) or 40)
    for _f in ImageSequence.Iterator(_im):
        _f = _f.convert("RGB"); _w, _h = _f.size
        _W = int(round(_h * ACTIVE_W / ACTIVE_H))                    # letterbox to the 4:3 panel
        _c = Image.new("RGB", (max(_W, _w), _h), (0, 0, 0)); _c.paste(_f, ((max(_W, _w) - _w) // 2, 0))
        screen_frames.append(pv.Texture(np.asarray(_c)))
    _cx, _cy = Ld.ACT_X0 + ACTIVE_W / 2, Ld.ACT_Y0 + ACTIVE_H / 2
    _plane = pv.Plane(center=(_cx, _cy, Ld.PANEL_Z - 0.06), direction=(0, 0, -1), i_size=ACTIVE_W, j_size=ACTIVE_H)
    # image top = the lid's front edge (it is "up" with the lid open), seen from the screen side
    _plane.texture_map_to_plane(origin=(_cx - ACTIVE_W / 2, _cy + ACTIVE_H / 2, Ld.PANEL_Z - 0.06),
                                point_u=(_cx + ACTIVE_W / 2, _cy + ACTIVE_H / 2, Ld.PANEL_Z - 0.06),
                                point_v=(_cx - ACTIVE_W / 2, _cy - ACTIVE_H / 2, Ld.PANEL_Z - 0.06), inplace=True)
    _bright = [float(np.asarray(t.to_image().point_data.active_scalars).mean()) for t in screen_frames]
    _start = int(np.argmax(_bright))                     # a frame with the logo fully drawn
    actors["screen_content"] = p.add_mesh(_plane, texture=screen_frames[_start], ambient=1.0, diffuse=0.0,
                                          specular=0.0, lighting=False)
    LID.add("screen_content")
    _sy = 8 + len(PARTS) * 21
    legend_row(lambda on: actors["screen_content"].SetVisibility(on), True, "#ffffff", "screen: loading animation")
    _step = [_start]
    def _next_frame(*_):
        _step[0] = (_step[0] + 1) % len(screen_frames)
        actors["screen_content"].texture = screen_frames[_step[0]]
    if not SHOT:
        p.add_timer_event(max_steps=10 ** 9, duration=screen_ms, callback=_next_frame)


def open_lid(deg):
    for f in LID:
        a = actors[f]
        a.SetOrigin(0, HY, HZ)
        a.SetOrientation(-deg, 0, 0)


LID_START = 110                       # open so the screen is visible
p.add_slider_widget(open_lid, [0, B.MAX_OPEN], value=LID_START, title="screen lid angle", pointa=(0.6, 0.08),
                    pointb=(0.95, 0.08), style="modern")
open_lid(LID_START)
def set_opacity(o):
    for k, a in actors.items():
        if k != "screen_content":                  # the screen keeps glowing
            a.GetProperty().SetOpacity(o)


p.add_slider_widget(set_opacity, [0.05, 1.0], value=OPACITY, title="transparency (1 = solid)",
                    pointa=(0.6, 0.20), pointb=(0.95, 0.20), style="modern", interaction_event="end")
ROLE = {"bottom": "body", "screen_back": "body", "box_hatch": "body", "keyboard_top": "kbplate",
        "screen_front": "kbplate", "battery_door": "accent", "door_lock": "accent2", "hinge_cap": "accent2",
        "hinge_axle": "accent2", "switch_knob": "accent2", "fill_logos_base": "accent", "fill_logos_lid": "accent",
        "fill_stripes_base": "accent", "fill_stripes_lid": "accent", "fill_caps_base": "body"}
_paltext = [None]
def apply_palette(key):
    pal = PALETTES[key]
    for f, role in ROLE.items():
        if f in actors:
            pr = actors[f].GetProperty()
            pr.SetColor(pv.Color(pal.get(role, pal["plate"])).float_rgb)     # kbplate defaults to plate
            acc = role.startswith("accent")
            pr.SetAmbient((0.5 if acc else 0.35) + (pal["glow"] if acc else 0.0))   # accents stay bright
            pr.SetDiffuse(0.6 if acc else 0.7)
    try:
        for a in _cap_bodies: a.GetProperty().SetColor(pv.Color(pal["keys"]).float_rgb)
        for a, spec in _cap_legends: a.texture = keycaps.legend(*spec, key=pal["keys"], ink=pal["ink"])
    except NameError:
        pass
    p.set_background(pal["bg"][0], top=pal["bg"][1])
    if _paltext[0] is not None:
        p.remove_actor(_paltext[0])
    dark = pal["bg"][0] in ("#07070b", "#1b1c20")
    _paltext[0] = p.add_text(f"palette {key}: {pal['name']}    (keys 1-6: " +
                             " / ".join(f"{k} {v['name']}" for k, v in PALETTES.items()) + ")",
                             position="lower_left", font_size=9, color="white" if dark else "black")
for _k in PALETTES:
    p.add_key_event(_k, lambda k=_k: apply_palette(k))
apply_palette(PAL0)
_STRIPES = [f for f in ("fill_stripes_base", "fill_stripes_lid") if f in actors]
def stripe_fill(on):
    for f in _STRIPES:
        actors[f].SetVisibility(on)
stripe_fill(os.environ.get("MINIDECK_STRIPEFILL", "1") != "0")
p.add_key_event("g", lambda: stripe_fill(not actors[_STRIPES[0]].GetVisibility()) if _STRIPES else None)
_title = p.add_text("Minideck: drag to rotate, scroll to zoom (scroll over the list to page it). Tick boxes hide/show parts.", position="upper_right",
           font_size=10, color="black")
p.camera_position = [(-70, -175, 150), (47, 42, 32), (0, 0, 1)] if not os.environ.get("MINIDECK_CAM") else eval(os.environ["MINIDECK_CAM"])   # whole deck with the lid open
_hint[0] = p.add_text("scroll here for more parts", position=(10, p.window_size[1] - 24), font_size=8, color="#555555")
layout_rows()
if not SHOT:
    _style = p.iren.interactor.GetInteractorStyle()
    def _wheel(step, zoom):
        def h(obj, ev):
            x, _y = p.iren.interactor.GetEventPosition()
            if x < PANEL_W:
                _scroll[0] += step * ROW_H * 3
                layout_rows(); p.render()
            else:
                zoom()
        return h
    # an observer on the style replaces its own wheel handling, so zoom is passed on by hand outside the list
    _style.AddObserver("MouseWheelForwardEvent", _wheel(-1, _style.OnMouseWheelForward))
    _style.AddObserver("MouseWheelBackwardEvent", _wheel(1, _style.OnMouseWheelBackward))
    p.iren.interactor.AddObserver("WindowResizeEvent", lambda *_: layout_rows())
if os.environ.get("MINIDECK_CLEAN"):             # clean product shot: no list, sliders or captions
    for w in p.widgets.slider_widgets + p.widgets.button_widgets:
        w.Off(); w.GetRepresentation().SetVisibility(0)
    for _w, _t in ROWS:
        _t.SetVisibility(0)
    for _t in (_hint[0], _paltext[0], _title):
        _t.SetVisibility(0)
if SHOT:
    p.screenshot(SHOT)
else:
    p.show()
