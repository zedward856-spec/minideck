# Thermal simulation

Steady state, room 25.0 °C, lid open, deck on a desk. 3D conduction on a 1 mm grid of the real parts; outside surfaces lose heat at h = 12.0 W/m²K (sides/top) and 5.0 W/m²K (bottom on a desk). Vents: chimney flow from the inside air temperature; fan: fixed flow. **Estimates for comparing options.**

| Load | Option | SoC °C | Cell °C | SDR °C | Inside air °C | Hottest case surface °C | Heat (W) |
|---|---|---|---|---|---|---|---|
| typical | current (PLA, sealed) | 81 | 40 | 30 | 40 | 47 | 2.2 |
| typical | Al pillar + Al floor plate | 66 | 39 | 30 | 40 | 58 | 2.2 |
| typical | pillar + plate + blower 0.1 L/s + vents 60 | 56 | 34 | 27 | 34 | 48 | 2.5 |
| typical+charging | current (PLA, sealed) | 88 | 44 | 32 | 48 | 73 | 3.6 |
| typical+charging | Al pillar + Al floor plate | 72 | 44 | 32 | 48 | 73 | 3.6 |
| typical+charging | pillar + plate + blower 0.1 L/s + vents 60 | 59 | 38 | 28 | 39 | 62 | 3.9 |
| heavy | current (PLA, sealed) | 168 | 67 | 113 | 67 | 105 | 6.7 |
| heavy | PETG case | 166 | 64 | 107 | 66 | 99 | 6.7 |
| heavy | vents 60 mm² in + out | 166 | 65 | 111 | 66 | 103 | 6.7 |
| heavy | vents 150 mm² in + out | 163 | 63 | 109 | 63 | 101 | 6.7 |
| heavy | Al pillar SoC → floor | 143 | 66 | 113 | 68 | 125 | 6.7 |
| heavy | Al pillar + Al floor plate | 129 | 66 | 112 | 67 | 106 | 6.7 |
| heavy | micro blower 0.1 L/s + vents 60 | 142 | 52 | 93 | 49 | 86 | 7.0 |
| heavy | micro blower 0.2 L/s + vents 150 | 131 | 45 | 82 | 42 | 76 | 7.0 |
| heavy | pillar + plate + blower 0.1 L/s + vents 60 | 105 | 52 | 92 | 49 | 85 | 7.0 |
| heavy | SDR switched off | 166 | 59 | 37 | 60 | 77 | 5.3 |
| heavy | CPU capped (SoC 1.2 W) | 119 | 64 | 111 | 61 | 104 | 5.7 |
| heavy+charging | current (PLA, sealed) | 175 | 74 | 115 | 76 | 107 | 8.1 |
| heavy+charging | Al pillar + Al floor plate | 135 | 73 | 115 | 75 | 111 | 8.1 |
| heavy+charging | pillar + plate + blower 0.1 L/s + vents 60 | 107 | 56 | 93 | 54 | 86 | 8.4 |
