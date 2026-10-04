"""Export every thermal-simulation run for the interactive viewer on the site (thermal.html).

    python3 thermal_export.py  ->  ../minideck-site/thermal/{index.json, parts.bin, <run>.bin}
Each run: temperatures on the 1 mm grid as uint8 (t = lo + v * step), C order (x, y, z).
"""
import os, json, numpy as np
import thermal_sim as TS

OUT = os.path.expanduser("~/minideck-site/thermal")
RUNS = [("typical", "current (PLA, sealed)", dict()),
        ("typical", "Al pillar + Al floor plate", dict(pillar=True, plate=True)),
        ("typical", "pillar + plate + blower + vents", dict(pillar=True, plate=True, fan=0.1e-3, vents=60)),
        ("typical+charging", "current (PLA, sealed)", dict()),
        ("typical+charging", "Al pillar + Al floor plate", dict(pillar=True, plate=True)),
        ("typical+charging", "pillar + plate + blower + vents", dict(pillar=True, plate=True, fan=0.1e-3, vents=60)),
        ("heavy", "current (PLA, sealed)", dict()),
        ("heavy", "PETG case", dict(case_mat="petg")),
        ("heavy", "vents 60 mm²", dict(vents=60)),
        ("heavy", "vents 150 mm²", dict(vents=150)),
        ("heavy", "Al pillar SoC → floor", dict(pillar=True)),
        ("heavy", "Al pillar + Al floor plate", dict(pillar=True, plate=True)),
        ("heavy", "micro blower 0.1 L/s + vents", dict(fan=0.1e-3, vents=60)),
        ("heavy", "micro blower 0.2 L/s + vents", dict(fan=0.2e-3, vents=150)),
        ("heavy", "pillar + plate + blower + vents", dict(pillar=True, plate=True, fan=0.1e-3, vents=60)),
        ("heavy", "SDR switched off", dict(sdr_scale=0.0)),
        ("heavy", "CPU capped (SoC 1.2 W)", dict(soc_scale=1.2 / 2.2)),
        ("heavy+charging", "current (PLA, sealed)", dict()),
        ("heavy+charging", "Al pillar + Al floor plate", dict(pillar=True, plate=True)),
        ("heavy+charging", "pillar + plate + blower + vents", dict(pillar=True, plate=True, fan=0.1e-3, vents=60))]
LABELS = {"bottom": "case", "keyboard_top": "keyboard plate", "box_hatch": "hatch", "battery_door": "battery door",
          "door_lock": "door lock", "switch_knob": "switch knob", "hinge_cap": "hinge cap", "hinge_axle": "hinge axle",
          "keyboard": "CardKB", "pn532": "PN532 NFC", "dac": "PCM5102 DAC", "lora": "E22 LoRa", "tp4056": "TP4056 charger",
          "mt3608": "Pololu boost", "gps_module": "GPS", "sdr_dongle": "NESDR SDR", "power_switch": "power switch",
          "18650": "18650 cell", "radxa": "Radxa ZERO 3W", "m2_hardware": "inserts", "antenna_lora": "LoRa antenna",
          "antenna_sdr": "SDR antenna", "antenna_wifi": "Wi-Fi antenna"}

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    lo, n, occ = TS.geometry()
    names = [nm for nm, _ in TS.PARTS if nm in occ]
    pid = np.zeros(n, np.uint8)                            # 0 = air
    for i, nm in enumerate(names, 1):
        pid[occ[nm]] = i
    pid[TS.boxmask(lo, n, TS.SOC_BOX) & occ["radxa"]] = len(names) + 1
    pid.tofile(f"{OUT}/parts.bin")
    index = dict(lo=lo.tolist(), n=[int(v) for v in n], cell_mm=1.0, t_amb=TS.T_AMB,
                 parts=["air"] + [LABELS.get(nm, nm) for nm in names] + ["RK3566 SoC"],
                 soc_box=TS.SOC_BOX, scenarios={k: v for k, v in TS.SCEN.items()},
                 h=dict(side=TS.H_SIDE, bottom=TS.H_BOTTOM), k=TS.K, runs=[])
    for i, (scen, label, kw) in enumerate(RUNS):
        r, full = TS.solve(scen, **kw)
        tlo, thi = TS.T_AMB, float(full.max())
        step = (thi - tlo) / 255.0
        q = np.clip(np.round((full - tlo) / step), 0, 255).astype(np.uint8)
        fn = f"run{i:02d}.bin"
        q.tofile(f"{OUT}/{fn}")
        index["runs"].append(dict(file=fn, scenario=scen, option=label, lo=tlo, step=step,
                                  soc=r["soc"], cell=r["cell"], sdr=r["sdr"], air=r["air"], surface=r["surface"],
                                  watts=r["watts"], airflow_lps=r["vdot"]))
        print(f"{i:2d} {scen:16s} {label:34s} SoC {r['soc']:.0f} cell {r['cell']:.0f} SDR {r['sdr']:.0f}")
        json.dump(index, open(f"{OUT}/index.json", "w"), indent=1)
