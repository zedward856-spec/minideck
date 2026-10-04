# Thermal simulation

Steady state, room 25.0 °C, lid open, deck on a desk. 3D conduction on a 1 mm grid of the real parts; outside surfaces lose heat at h = 12.0 W/m²K (sides/top) and 5.0 W/m²K (bottom on a desk). Vents: chimney flow from the inside air temperature; fan: fixed flow. **Estimates for comparing options.**

| Load | Option | SoC °C | Cell °C | SDR °C | Inside air °C | Hottest case surface °C | Heat (W) |
|---|---|---|---|---|---|---|---|
| typical | current (PLA, sealed) | 81 | 39 | 30 | 40 | 47 | 2.2 |
| typical | Al pillar + Al floor plate | 66 | 39 | 30 | 40 | 58 | 2.2 |
| typical | pillar + plate + blower 0.1 L/s + vents 60 | 56 | 34 | 28 | 34 | 48 | 2.5 |
| typical+charging | current (PLA, sealed) | 88 | 44 | 33 | 48 | 73 | 3.6 |
| typical+charging | Al pillar + Al floor plate | 72 | 44 | 33 | 48 | 73 | 3.6 |
| typical+charging | pillar + plate + blower 0.1 L/s + vents 60 | 59 | 38 | 29 | 39 | 62 | 3.9 |
| heavy | current (PLA, sealed) | 168 | 68 | 114 | 67 | 109 | 6.7 |
| heavy | PETG case | 166 | 66 | 107 | 66 | 103 | 6.7 |
| heavy | vents 60 mm² in + out | 166 | 66 | 112 | 66 | 108 | 6.7 |
| heavy | vents 150 mm² in + out | 163 | 65 | 110 | 64 | 106 | 6.7 |
| heavy | Al pillar SoC → floor | 143 | 68 | 114 | 68 | 125 | 6.7 |
| heavy | Al pillar + Al floor plate | 129 | 67 | 113 | 67 | 109 | 6.7 |
| heavy | micro blower 0.1 L/s + vents 60 | 143 | 53 | 94 | 49 | 91 | 7.0 |
| heavy | micro blower 0.2 L/s + vents 150 | 131 | 46 | 84 | 42 | 81 | 7.0 |
| heavy | pillar + plate + blower 0.1 L/s + vents 60 | 105 | 53 | 94 | 49 | 90 | 7.0 |
| heavy | SDR switched off | 166 | 59 | 38 | 60 | 77 | 5.3 |
| heavy | CPU capped (SoC 1.2 W) | 119 | 65 | 112 | 61 | 108 | 5.7 |
| heavy+charging | current (PLA, sealed) | 175 | 75 | 116 | 76 | 112 | 8.1 |
| heavy+charging | Al pillar + Al floor plate | 135 | 74 | 116 | 76 | 112 | 8.1 |
| heavy+charging | pillar + plate + blower 0.1 L/s + vents 60 | 107 | 57 | 95 | 54 | 91 | 8.4 |
