# Print simulation

Every print file sliced with PrusaSlicer 2.8.1 (Bambu-like PLA setup: 0.4 nozzle, 2 walls, 15 % grid infill, 5 top / 3 bottom layers, fast motion limits) and read back layer by layer. Colours show what each line is. Times are estimates; Bambu Studio will differ a little. Re-run: `python3 cad/print_sim.py`.

![legend](legend.png)

## Totals

| Filament | Parts | Time | Filament |
|---|---|---|---|
| Charcoal `#2D2D2D` | 3 | 3 h 28 min | 73 g (24.4 m) |
| Dark grey `#3D3D3D` | 2 | 0 h 38 min | 11 g (3.7 m) |
| Cyber yellow `#F7D116` | 5 | 0 h 25 min | 2 g (0.6 m) |
| any | 1 | 0 h 31 min | 17 g (5.7 m) |
| **whole deck** (without the test piece) | 10 | **4 h 32 min** | **86 g** |

## Parts

### case_bottom  ·  charcoal

0.2 mm layers · **198 layers** · **2h 19m 28s** · 45.0 g (15.09 m) · 0.2 mm layers; supports only for the front port openings. The NFC mark is engraved in its underside (prints on the bed)

![case_bottom](case_bottom.png) ![case_bottom printing](case_bottom_build.gif)

![case_bottom layers](case_bottom_layers.png)

Has: outer wall, inner wall, overhang wall, infill, solid infill, top skin, bridge

### lid_shell  ·  charcoal

0.2 mm layers · **75 layers** · **1h 4m 41s** · 26.1 g (8.74 m) · 0.2 mm layers, back face down

![lid_shell](lid_shell.png) ![lid_shell printing](lid_shell_build.gif)

![lid_shell layers](lid_shell_layers.png)

Has: outer wall, inner wall, overhang wall, infill, solid infill, top skin, bridge

### hinge_box_hatch  ·  charcoal

0.2 mm layers · **16 layers** · **4m 6s** · 1.8 g (0.60 m) · 0.2 mm layers

![hinge_box_hatch](hinge_box_hatch.png) ![hinge_box_hatch printing](hinge_box_hatch_build.gif)

![hinge_box_hatch layers](hinge_box_hatch_layers.png)

Has: outer wall, inner wall, solid infill, top skin

### keyboard_plate  ·  dark-grey

0.12 mm layers · **11 layers** · **25m 6s** · 6.5 g (2.19 m) · **0.12 mm layers**: the webs between keys are 0.42 mm

![keyboard_plate](keyboard_plate.png) ![keyboard_plate printing](keyboard_plate_build.gif)

![keyboard_plate layers](keyboard_plate_layers.png)

Has: outer wall, inner wall, infill, solid infill, top skin, bridge

### screen_bezel  ·  dark-grey

0.12 mm layers · **24 layers** · **13m 39s** · 4.5 g (1.52 m) · 0.12–0.16 mm layers, face down

![screen_bezel](screen_bezel.png) ![screen_bezel printing](screen_bezel_build.gif)

![screen_bezel layers](screen_bezel_layers.png)

Has: outer wall, inner wall, overhang wall, infill, solid infill, top skin, bridge

### battery_door  ·  yellow

0.2 mm layers · **105 layers** · **8m 52s** · 0.7 g (0.24 m) · **print upright, with a brim** (0.4 mm skin)

![battery_door](battery_door.png) ![battery_door printing](battery_door_build.gif)

![battery_door layers](battery_door_layers.png)

Has: outer wall, inner wall, overhang wall, solid infill, top skin, brim

### battery_lock_clip  ·  yellow

0.12 mm layers · **37 layers** · **3m 12s** · 0.2 g (0.07 m) · 0.12 mm layers

![battery_lock_clip](battery_lock_clip.png) ![battery_lock_clip printing](battery_lock_clip_build.gif)

![battery_lock_clip layers](battery_lock_clip_layers.png)

Has: outer wall, inner wall, overhang wall, solid infill, top skin

### torque_hinge_cap  ·  yellow

0.12 mm layers · **9 layers** · **57s** · 0.1 g (0.04 m) · 0.12 mm layers, logo up

![torque_hinge_cap](torque_hinge_cap.png) ![torque_hinge_cap printing](torque_hinge_cap_build.gif)

![torque_hinge_cap layers](torque_hinge_cap_layers.png)

Has: outer wall, inner wall, solid infill, top skin

### hinge_axle  ·  yellow

0.12 mm layers · **126 layers** · **10m 51s** · 0.8 g (0.26 m) · 0.12 mm layers, flange down

![hinge_axle](hinge_axle.png) ![hinge_axle printing](hinge_axle_build.gif)

![hinge_axle layers](hinge_axle_layers.png)

Has: outer wall, inner wall, overhang wall, infill, solid infill, top skin, bridge

### switch_knob  ·  yellow

0.12 mm layers · **28 layers** · **1m 48s** · 0.1 g (0.02 m) · 0.12 mm layers, **on its long edge** (as exported: socket opening up) so the fin and plate share every layer; goes in from inside the case, the switch lever drops into its open-top socket

![switch_knob](switch_knob.png) ![switch_knob printing](switch_knob_build.gif)

![switch_knob layers](switch_knob_layers.png)

Has: outer wall, inner wall, overhang wall

### battery_door_fit_test  ·  tests

0.2 mm layers · **114 layers** · **31m 3s** · 17.1 g (5.72 m) · optional: the door, lock and chamber end, to check the fit first

![battery_door_fit_test](battery_door_fit_test.png) ![battery_door_fit_test printing](battery_door_fit_test_build.gif)

![battery_door_fit_test layers](battery_door_fit_test_layers.png)

Has: outer wall, inner wall, overhang wall, infill, solid infill, top skin, bridge, brim

