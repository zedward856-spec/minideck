# Print files

One folder per filament colour, so each folder is one print batch. Every part is already in its print orientation, flat on the bed.
PLA, 0.4 mm nozzle. Rebuild this folder from the CAD with `python3 export_print.py`.

## `charcoal/` · Charcoal `#2D2D2D` (e.g. Bambu PLA Matte Charcoal)

| File | Qty | Size (mm) | Settings |
|---|---|---|---|
| `case_bottom.stl` | 1 | 93.7 × 81.5 × 39.5 | 0.2 mm layers; supports only for the front port openings. The NFC mark is engraved in its underside (prints on the bed) |
| `lid_shell.stl` | 1 | 93.7 × 79.5 × 15.0 | 0.2 mm layers, back face down |
| `hinge_box_hatch.stl` | 1 | 85.3 × 12.8 × 1.2 | 0.2 mm layers |

## `dark-grey/` · Dark grey `#3D3D3D` (e.g. Bambu PLA Basic Dark Gray)

| File | Qty | Size (mm) | Settings |
|---|---|---|---|
| `keyboard_plate.stl` | 1 | 93.7 × 64.1 × 1.4 | **0.12 mm layers**: the webs between keys are 0.42 mm |
| `screen_bezel.stl` | 1 | 91.1 × 61.5 × 3.0 | 0.12–0.16 mm layers, face down |

## `yellow/` · Cyber yellow `#F7D116` (e.g. Bambu PLA Basic Sunflower Yellow)

| File | Qty | Size (mm) | Settings |
|---|---|---|---|
| `battery_door.stl` | 1 | 3.2 × 24.2 × 21.0 | **print upright, with a brim** (0.4 mm skin) |
| `battery_lock_clip.stl` | 1 | 11.8 × 9.3 × 4.5 | 0.12 mm layers |
| `torque_hinge_cap.stl` | 1 | 10.9 × 10.8 × 1.2 | 0.12 mm layers, logo up |
| `hinge_axle.stl` | 1 | 11.9 × 13.0 × 15.2 | 0.12 mm layers, flange down |
| `switch_knob.stl` | 1 | 3.4 × 12.0 × 2.0 | 0.12 mm layers, flat back down, fin up; goes in from inside the case, the switch lever drops into its open-top socket |

## `tests/` · any

| File | Qty | Size (mm) | Settings |
|---|---|---|---|
| `battery_door_fit_test.stl` | 1 | 77.9 × 29.6 × 22.7 | optional: the door, lock and chamber end, to check the fit first |

## Also needed

- 8 × M2 heat-set inserts (3.5 OD × 3 mm): 4 in the hinge-box floor, 4 in the lid shell
- 12 × M2 × 4 countersunk screws
- ~26 mm of 1.75 mm filament as the battery-door hinge pin
- 1 × SS12D00 mini slide switch (SPDT, 8.6 × 3.6 × 3.5 mm body) for power: trim its lever to 1.05 mm

**Optional paint fill.** The logos, MINIDECK text, side stripes and the NFC mark under the PN532 are engraved 0.3–0.6 mm deep. Go over them with a paint marker and wipe the surface with IPA.

Full build steps: [../BUILD.md](../BUILD.md)
