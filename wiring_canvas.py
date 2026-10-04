"""Obsidian Canvas wiring diagrams, drawn from the wiring plan (out/wires.json, written by wiring.py).

Every module is a group with one node per pin/pad it uses; every wire is an arrow from pin to pin, coloured by
signal type and labelled. The Radxa's whole 40-pin header is drawn (free pins marked).

    python3 wiring_canvas.py   -> wiring/minideck-wiring-all.canvas, wiring/minideck-wiring-power.canvas
                                  (+ a copy in ~/Documents/Obsidian/Minideck/)
"""
import json, os, re, shutil

COL = {"pwr": "#e03131", "gnd": "#868e96", "v33": "#f08c00", "i2c": "#1c7ed6", "i2s": "#2f9e44",
       "uart": "#f2c94c", "gpio": "#e9ecef", "usb": "#9c36b5", "hdmi": "#c46b2c", "coax": "#a5b4c8"}
KIND_NAME = {"pwr": "5 V / battery +", "gnd": "GND", "v33": "3.3 V", "i2c": "I²C", "i2s": "I²S audio", "uart": "UART",
             "gpio": "GPIO", "usb": "USB (SDR)", "hdmi": "HDMI ribbon", "coax": "antenna coax"}

# Radxa ZERO 3W header (Radxa schematic, page 20). Used pins get their wire; the rest are marked free.
HEADER = {1: "3V3", 2: "5V", 3: "UART3 RX", 4: "5V", 5: "UART3 TX", 6: "GND", 7: "GPIO3_C4", 8: "UART2 TX (console)",
          9: "GND", 10: "UART2 RX (console)", 11: "GPIO3_A1", 12: "I2S3 BCK", 13: "GPIO3_A2", 14: "GND",
          15: "GPIO3_B0", 16: "UART4 RX", 17: "3V3", 18: "UART4 TX", 19: "SPI3 MOSI", 20: "GND",
          21: "SPI3 MISO", 22: "GPIO3_C1", 23: "SPI3 CLK", 24: "SPI3 CS0", 25: "GND", 26: "SPI3 CS1",
          27: "USB2 HOST2 D+", 28: "USB2 HOST2 D-", 29: "I2C5 SCL", 30: "GND", 31: "I2C5 SDA", 32: "GPIO3_C2",
          33: "GPIO3_C3", 34: "GND", 35: "I2S3 LRCK", 36: "GPIO3_A7", 37: "GPIO1_A4", 38: "GPIO3_A6",
          39: "GND", 40: "I2S3 DIN"}

# endpoint text -> (module, pin)
RULES = [
    (r"^Radxa pin (\d+)", lambda m: ("radxa", f"pin {m.group(1)}")),
    (r"^Radxa micro-HDMI", lambda m: ("radxa_io", "micro-HDMI")),
    (r"^Radxa u\.FL", lambda m: ("radxa_io", "Wi-Fi u.FL")),
    (r"^18650 \+", lambda m: ("cell", "+ (button)")),
    (r"^18650 -", lambda m: ("cell", "− (door spring)")),
    (r"^TP4056 (\S+)", lambda m: ("tp4056", m.group(1))),
    (r"^MT3608 (\S+)", lambda m: ("boost", m.group(1))),
    (r"^BOOST (.+)", lambda m: ("boost", m.group(1))),
    (r"^input capacitor ([+-])", lambda m: ("cap", ("+ " if m.group(1) == "+" else "− ") + "47 µF")),
    (r"^5 V splice", lambda m: ("splice5", "5 V splice")),
    (r"^GND splice", lambda m: ("spliceG", "GND splice")),
    (r"^power switch middle", lambda m: ("switch", "middle (common)")),
    (r"^power switch outer", lambda m: ("switch", "outer (ON end)")),
    (r"^driver board (\S+)", lambda m: ("driver", "mini-HDMI" if "HDMI" in m.group(0) else m.group(1))),
    (r"^PN532 (\S+)", lambda m: ("pn532", m.group(1))),
    (r"^CardKB Grove pad (\S+)", lambda m: ("cardkb", m.group(1))),
    (r"^PCM5102 (.+)", lambda m: ("dac", m.group(1))),
    (r"^GPS module (\S+)", lambda m: ("gps", m.group(1))),
    (r"^E22 (\S+)", lambda m: ("lora", m.group(1))),
    (r"^SDR USB (\S+)", lambda m: ("sdr", m.group(1))),
    (r"^patch antenna", lambda m: ("gps_ant", "feed")),
    (r"^LoRa FPC antenna", lambda m: ("lora_ant", "u.FL")),
    (r"^Wi-Fi FPC antenna", lambda m: ("wifi_ant", "u.FL")),
]
TITLE = {"radxa": "Radxa ZERO 3W — 40-pin header", "radxa_io": "Radxa ZERO 3W — ports", "cell": "18650 cell",
         "tp4056": "TP4056 USB-C charger (charging only)", "boost": "Pololu U3V40F5 5 V boost", "splice5": "5 V splice", "spliceG": "GND splice",
         "switch": "SS12D00 power switch", "driver": "EHD-40P-V3 screen driver (lid)", "pn532": "PN532 NFC",
         "cardkb": "M5Stack CardKB", "dac": "PCM5102 DAC", "gps": "ATGM336H GPS", "lora": "Ebyte E22 LoRa",
         "sdr": "NESDR Nano 2+ (USB wired to pins)", "gps_ant": "GPS patch antenna (lid)",
         "lora_ant": "LoRa FPC antenna", "wifi_ant": "Wi-Fi/BT FPC antenna", "cap": "boost input capacitor"}
# where each module sits: columns (x, top y, modules stacked top to bottom with a gap)
COLUMNS = [(-1500, -40, ["cell"]), (-1160, -40, ["tp4056", "switch"]), (-820, -420, ["gps_ant", "cap", "boost", "gps", "dac"]),
           (-520, 120, ["splice5", "spliceG"]), (-300, -420, ["radxa_io"]), (0, 0, ["radxa"]),
           (60, -620, ["driver"]), (420, -620, ["wifi_ant"]), (720, 120, ["pn532", "lora", "sdr"]),
           (1100, 120, ["cardkb", "lora_ant"])]
PW, PH, GAP, PAD, HEAD = 190, 36, 8, 18, 46


def endpoint(text):
    for rx, f in RULES:
        m = re.match(rx, text)
        if m:
            return f(m)
    return (text.split()[0].lower(), text)


def build(wires, title, notes, full_header=True):
    # pins per module, in first-use order
    pins = {}
    ends = []
    for w in wires:
        a, b = endpoint(w["a"]), endpoint(w["b"])
        ends.append((a, b))
        for mod, pin in (a, b):
            pins.setdefault(mod, [])
            if pin not in pins[mod]:
                pins[mod].append(pin)
    nodes, ids, pos = [], {}, {}
    PLACE = {}
    for cx, cy, mods in COLUMNS:                     # stack each column's modules, sized by their pin count
        y = cy
        for mod in mods:
            if mod not in pins:
                continue
            PLACE[mod] = (cx, y)
            n = 20 if mod == "radxa" else len(pins[mod])
            y += HEAD + n * (PH + GAP) + PAD + 70
    used_pins = {p for m, p in [e for ab in ends for e in ab] if m == "radxa"}
    for mod, plist in pins.items():
        gx, gy = PLACE.get(mod, (1500, 900))
        if mod == "radxa":
            rows = 20
            gw, gh = 2 * PW + 3 * PAD, HEAD + rows * (PH + GAP) + PAD
            nodes.append(dict(id=f"g_{mod}", type="group", x=gx, y=gy, width=gw, height=gh, label=TITLE[mod]))
            for n in range(1, 41):
                if not full_header and f"pin {n}" not in used_pins:
                    continue
                col, row = (n - 1) % 2, (n - 1) // 2
                x, y = gx + PAD + col * (PW + PAD), gy + HEAD + row * (PH + GAP)
                used = f"pin {n}" in used_pins
                nid = f"p_radxa_{n}"
                ids[(mod, f"pin {n}")] = nid
                pos[nid] = (x, y)
                nodes.append(dict(id=nid, type="text", x=x, y=y, width=PW, height=PH,
                                  text=f"**{n}** · {HEADER[n]}" + ("" if used else "  _(free)_"),
                                  **({} if used else {"color": "0"})))
            continue
        gw, gh = PW + 2 * PAD, HEAD + len(plist) * (PH + GAP) + PAD
        nodes.append(dict(id=f"g_{mod}", type="group", x=gx, y=gy, width=gw, height=gh, label=TITLE.get(mod, mod)))
        for i, pin in enumerate(plist):
            x, y = gx + PAD, gy + HEAD + i * (PH + GAP)
            nid = f"p_{mod}_{i}"
            ids[(mod, pin)] = nid
            pos[nid] = (x, y)
            nodes.append(dict(id=nid, type="text", x=x, y=y, width=PW, height=PH, text=pin))
    edges = []
    for k, (w, (a, b)) in enumerate(zip(wires, ends)):
        fa, fb = ids[a], ids[b]
        (xa, ya), (xb, yb) = pos[fa], pos[fb]
        if abs(xa - xb) < PW:                     # same column: loop out of the side
            fs = ts = "right" if xa >= 0 else "left"
        elif xa < xb:
            fs, ts = "right", "left"
        else:
            fs, ts = "left", "right"
        edges.append(dict(id=f"w{k}", fromNode=fa, fromSide=fs, toNode=fb, toSide=ts, toEnd="none",
                          color=COL.get(w["kind"], "#ffffff"), label=w["name"]))
    # title, legend and notes
    xs = [n["x"] for n in nodes]; ys = [n["y"] for n in nodes]
    x0, y0 = min(xs), min(ys)
    legend = "\n".join(f"- <span style=\"color:{COL[k]}\">■</span> {KIND_NAME[k]}" for k in COL if any(w["kind"] == k for w in wires))
    nodes.append(dict(id="title", type="text", x=x0, y=y0 - 360, width=900, height=120,
                      text=f"# {title}\n{len(wires)} wires · generated from the wiring plan (`python3 wiring_canvas.py`)"))
    nodes.append(dict(id="legend", type="text", x=x0 + 940, y=y0 - 360, width=320, height=60 + 26 * legend.count("\n"),
                      text="**Wire colours**\n" + legend))
    if notes:
        nodes.append(dict(id="notes", type="text", x=x0 + 1300, y=y0 - 360, width=720, height=60 + 26 * len(notes),
                          text="**Notes**\n" + "\n".join(f"- {n}" for n in notes)))
    return dict(nodes=nodes, edges=edges)


NOTES_ALL = ["Pin 1 is at the Radxa's microSD end (its left end in the case): check the square pad before soldering.",
             "One wire per Radxa pad; the CardKB is chained onto the PN532's I²C pins.",
             "SDR: USB over header pins 27/28 after swapping R32/R39 → R45/R46 on the Radxa.",
             "Gauges: 22–24 AWG for power, 28–30 AWG for signals, 1.13 mm u.FL coax for antennas."]
NOTES_PWR = ["Boost: Pololu U3V40F5, fixed 5 V (nothing to adjust), ~2.6 A out from a charged cell.",
             "Load is taken from the TP4056's B+/B− pads, so its ~3 A protection is not in the power path: use a protected high-drain 18650 (button top, ≤70 mm).",
             "TP4056 = charging only; its OUT pads stay empty. Charging works with the switch off.",
             "Power switch: middle pin from B+, one outer pin to the boost VIN (check the ON end with a meter).",
             "47 µF capacitor right across the boost's input pads.",
             "Battery → charger → switch → boost: 20–22 AWG; splice → loads: 24 AWG."]

if __name__ == "__main__":
    wires = json.load(open("out/wires.json"))
    os.makedirs("wiring", exist_ok=True)
    out = {"minideck-wiring-all.canvas": build(wires, "Minideck — every wire", NOTES_ALL),
           "minideck-wiring-power.canvas": build([w for w in wires if w["kind"] in ("pwr", "gnd", "v33")],
                                                 "Minideck — power wiring", NOTES_PWR, full_header=False)}
    vault = os.path.expanduser("~/Documents/Obsidian/Minideck")
    os.makedirs(vault, exist_ok=True)
    for name, c in out.items():
        json.dump(c, open(f"wiring/{name}", "w"), indent=1)
        shutil.copy(f"wiring/{name}", f"{vault}/{name}")
        print(name, len(c["nodes"]), "nodes", len(c["edges"]), "wires")
