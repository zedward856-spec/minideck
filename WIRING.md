# Minideck wiring plan

Radxa ZERO 3W, mounted upside down: the 40 header pads (no header fitted) face UP under the
keyboard - solder wires on that side and lay them flat (~3 mm of room above the board).
Pin 1 is at the microSD end (Pi-Zero layout). Radxa's board drawing puts the microSD socket at the
board's **left** end in this case (the camera FPC is at the right end), so pin 1 is at the left end.
The 3D wire routes in the viewer were drawn with pin 1 at the right end: go by the pin numbers below,
not the 3D routes, and check the square pad / '1' mark on your board before soldering.

## Radxa header use

| Pin | Function | Wires |
|---|---|---|
| 1 | 3V3 | DAC VIN 3V3 |
| 2 | 5V | 5V -> Radxa |
| 3 | GPIO1_A0 / UART3 RX | GPS TX -> Radxa RX |
| 4 | 5V | GPS VCC 5V |
| 5 | GPIO1_A1 / UART3 TX | GPS RX <- Radxa TX |
| 6 | GND | GND -> Radxa |
| 7 | GPIO3_C4 | LoRa M1 |
| 9 | GND | GPS GND |
| 12 | GPIO3_A3 / I2S3 SCLK (BCK) | DAC BCK |
| 13 | GPIO3_A2 | LoRa M0 |
| 14 | GND | SDR GND |
| 16 | GPIO3_B1 / UART4 RX | LoRa TXD -> Radxa RX |
| 17 | 3V3 | PN532 3V3 |
| 18 | GPIO3_B2 / UART4 TX | LoRa RXD <- Radxa TX |
| 22 | GPIO3_C1 | LoRa AUX |
| 25 | GND | PN532 GND |
| 27 | USB2 HOST2 D+ (after R32->R45 swap) | SDR D+ |
| 28 | USB2 HOST2 D- (after R39->R46 swap) | SDR D- |
| 29 | GPIO3_B3 / I2C5 SCL | PN532 SCL |
| 30 | GND | DAC GND |
| 31 | GPIO3_B4 / I2C5 SDA | PN532 SDA |
| 34 | GND | LoRa GND |
| 35 | GPIO3_A4 / I2S3 LRCK | DAC LRCK |
| 36 | GPIO3_A7 | PN532 IRQ |
| 40 | GPIO3_A5 / I2S3 SDO (DIN) | DAC DIN |

## Every wire

| Wire | From | To | Type / note |
|---|---|---|---|
| BAT+ | 18650 + contact (right end) | TP4056 B+ | 24 AWG silicone, red |
| BAT- | 18650 - contact (door spring) | TP4056 B- | 24 AWG black - through the hole in the chamber divider |
| TP OUT+ -> switch | TP4056 OUT+ | power switch middle pin (common) | 24 AWG red, over the top of the charger |
| switch -> boost IN+ | power switch outer pin (the ON end) | MT3608 VIN+ | 24 AWG red; check with a multimeter which outer pin is ON with the knob toward the back |
| TP OUT- -> boost IN- | TP4056 OUT- | MT3608 VIN- | 24 AWG black |
| boost 5V -> splice | MT3608 OUT+ (set to 5.1 V) | 5 V splice | 22 AWG red - one thick lead, split at a heat-shrunk splice behind the Radxa |
| boost GND -> splice | MT3608 OUT- | GND splice | 22 AWG black |
| 5V -> Radxa | 5 V splice | Radxa pin 2 (+5V) | 24 AWG |
| GND -> Radxa | GND splice | Radxa pin 6 (GND) | 24 AWG |
| Screen 5V | 5 V splice | driver board 5V (USB-C pads) | 24-26 AWG, through the hinge |
| Screen GND | GND splice | driver board GND | 24-26 AWG, through the hinge |
| PN532 SCL | PN532 SCL (DIP switches: I2C) | Radxa pin 29 | 28-30 AWG |
| PN532 SDA | PN532 SDA (DIP switches: I2C) | Radxa pin 31 | 28-30 AWG |
| PN532 3V3 | PN532 3V3 (DIP switches: I2C) | Radxa pin 17 | 28-30 AWG |
| PN532 GND | PN532 GND (DIP switches: I2C) | Radxa pin 25 | 28-30 AWG |
| PN532 IRQ | PN532 IRQ (DIP switches: I2C) | Radxa pin 36 | 28-30 AWG |
| CardKB SCL | CardKB Grove pad SCL (underside) | PN532 SCL pin (chain) | 28-30 AWG; out of the keyboard through the groove, chained onto the PN532's pins |
| CardKB SDA | CardKB Grove pad SDA (underside) | PN532 SDA pin (chain) | 28-30 AWG; out of the keyboard through the groove, chained onto the PN532's pins |
| CardKB 3V3 | CardKB Grove pad 3V3 (underside) | PN532 3V3 pin (chain) | 28-30 AWG; out of the keyboard through the groove, chained onto the PN532's pins |
| CardKB GND | CardKB Grove pad GND (underside) | PN532 GND pin (chain) | 28-30 AWG; out of the keyboard through the groove, chained onto the PN532's pins |
| DAC BCK | PCM5102 BCK | Radxa pin 12 | 28-30 AWG; DAC module: SCK to GND, FMT low, XSMT high |
| DAC LRCK | PCM5102 LRCK | Radxa pin 35 | 28-30 AWG; DAC module: SCK to GND, FMT low, XSMT high |
| DAC DIN | PCM5102 DIN | Radxa pin 40 | 28-30 AWG; DAC module: SCK to GND, FMT low, XSMT high |
| DAC VIN 3V3 | PCM5102 VIN 3V3 | Radxa pin 1 | 28-30 AWG; DAC module: SCK to GND, FMT low, XSMT high |
| DAC GND | PCM5102 GND | Radxa pin 30 | 28-30 AWG; DAC module: SCK to GND, FMT low, XSMT high |
| GPS TX -> Radxa RX | GPS module TX | Radxa pin 3 | 28-30 AWG |
| GPS RX <- Radxa TX | GPS module RX | Radxa pin 5 | 28-30 AWG |
| GPS VCC 5V | GPS module VCC | Radxa pin 4 | 28-30 AWG |
| GPS GND | GPS module GND | Radxa pin 9 | 28-30 AWG |
| LoRa TXD -> Radxa RX | E22 TXD | Radxa pin 16 | 28-30 AWG |
| LoRa RXD <- Radxa TX | E22 RXD | Radxa pin 18 | 28-30 AWG |
| LoRa M0 | E22 M0 | Radxa pin 13 | 28-30 AWG |
| LoRa M1 | E22 M1 | Radxa pin 7 | 28-30 AWG |
| LoRa AUX | E22 AUX | Radxa pin 22 | 28-30 AWG |
| LoRa GND | E22 GND | Radxa pin 34 | 28-30 AWG |
| LoRa VCC 5V | 5 V splice | E22 VCC | 24-26 AWG |
| SDR D+ | SDR USB D+ (plug removed) | Radxa pin 27 | D+/D- as a twisted pair, keep it short; 28 AWG |
| SDR D- | SDR USB D- (plug removed) | Radxa pin 28 | D+/D- as a twisted pair, keep it short; 28 AWG |
| SDR GND | SDR USB GND (plug removed) | Radxa pin 14 | 24-26 AWG |
| SDR 5V | 5 V splice | SDR USB VBUS | 24-26 AWG |
| HDMI ribbon | Radxa micro-HDMI (soldered) | driver board mini-HDMI (C2 plug) | FPV FPC ribbon, rolled through the 8.4 mm hinge bore |
| GPS antenna coax | GPS module u.FL | patch antenna (lid) | 1.13 mm u.FL-u.FL coax, ~150 mm |
| LoRa antenna coax | E22 u.FL | LoRa FPC antenna (box back wall) | 1.13 mm u.FL coax, ~120 mm (Molex 211140 has its own 100 mm lead) |
| Wi-Fi antenna coax | Radxa u.FL (Wi-Fi) | Wi-Fi FPC antenna (box roof) | 1.13 mm u.FL coax; enable the external antenna overlay in rsetup |

## Notes

- **Power switch**: an SS12D00 slide switch (SPDT, 8.6 x 3.6 mm body) in the left wall, beside the TP4056, breaks TP4056 OUT+ -> MT3608 VIN+. Middle pin = from the charger, one outer pin = to the boost (the other outer pin stays empty). The printed pill knob (print/yellow/switch_knob.stl) presses onto its lever. Charging still works with the switch off (the TP4056 charges the cell directly).
- Set the MT3608 to 5.1 V *before* connecting the Radxa. It is ~1.4 A max - a 3 A boost is safer.
- One wire per Radxa pad. I2C (CardKB 0x5F, PN532 0x24) on I2C5 (pins 29/31) runs Radxa -> PN532, and the CardKB is chained onto the PN532's header pins. Power both from 3.3 V (pin 17) so the bus pull-ups stay at 3.3 V (the Radxa is not 5 V tolerant). Enable the i2c5 overlay.
- 5 V: one 22 AWG lead from the boost to a heat-shrunk splice just behind the Radxa, branching to Radxa pin 2, the LoRa, the screen and the SDR. Same for GND (Radxa pin 6 + screen). The GPS runs from 5 V on pin 4 (its module has a regulator; its UART stays 3.3 V).
- DAC: I2S3 (pins 12/35/40), enable the i2s3 overlay; tie the module's SCK to GND.
- GPS on UART3 (pins 3/5), LoRa E22 on UART4 (pins 15/17); M0/M1/AUX on pins 13/7/22. Pins 8/10 (UART2) are the debug console - left free.
- Screen: HDMI ribbon + its own 5 V pair straight from the boost, all through the hinge bore.
- SDR on header pins 27/28 = the RK3566's spare USB2 HOST2 port (schematic page 20). On the Radxa: remove R32 and R39 (0 ohm, they route I2C4 to those pins) and fit 0 ohm / a solder bridge on R45 and R46 (marked NC). Cut the dongle's USB-A plug off and solder VBUS/D-/D+/GND straight to pins 2/28/27/14. Keep D+/D- twisted and short. Software: the HOST2 (EHCI/OHCI) controller must be enabled in the device tree - check rsetup overlays, or ask me for an overlay.
- Pin map checked against Radxa's schematic (page 20): 3V3 = pins 1 & 17; UART4 RX/TX = 16/18; GND = 6, 9, 14, 20, 25, 30, 34, 39 (the web pin table has some of these wrong).
- Wire: 24 AWG silicone for power, 28-30 AWG silicone for signals, 1.13 mm coax for antennas.
- The CardKB Grove pads sit over the battery block: a 1.2 mm groove in its top lets those 4 wires out.
