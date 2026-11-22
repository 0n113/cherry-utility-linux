# Other devices: keyboards and mice on the Evision protocol

From static analysis of `cus.exe` 3.12 only. **None of this has been tried on
a device.** Framing and the settings table commands (`0x05` read, `0x06`
write) are described in [protocol.md](protocol.md). Function addresses refer
to `cus.exe`.

## Settings table layout

Devices with on-board profiles (`HwProfiles_Evision`, 3 profiles on all 15
devices that have it) keep one 0x40-byte block per profile. Below, `p` is the
active profile, or 0 on devices without profiles.

| Offset | Size | Devices | Content |
|---|---|---|---|
| `0x00` | 1 | keyboards | active profile index |
| `p*0x40 + 0x01` | 8 | keyboards | lighting header |
| `p*0x40 + 0x15` | 1 | keyboards | lights off flag (offset configurable) |
| `p*0x40 + 0x16` | 1 | keyboards | key lock bitmask |
| `p*0x40 + 0x35` | 1 | keyboards | polling rate index, wired |
| `p*0x40 + 0x36` | 1 | keyboards | polling rate index, dongle |
| `0x28` | 8 | MX Board 3.1 | side lighting header |
| `0x0E` | 10 | MC 2.1 / MC 3.1 mice | polling rate, DPI slots, selected slot |

## Profiles (`HwProfiles_Evision`)

- Read active profile: `0x05`, offset 0, 1 byte.
- Switch: `0x06`, offset 0, 1 byte.
- At start the software writes the byte `i` to offset `i*0x40` for every
  profile `i >= 1`, then writes its stored profile index.
- After a switch, every per-profile feature writes its settings again at the
  new profile's offsets.
- Other tables use a per-profile stride from the device config:
  `customLightingsOffset` (0x180 or 0x200), `mappingOffset`,
  `macroTableOffset`.

## Lighting (`Lightings_Evision`)

All lighting writes are wrapped in a write session: Stx before, Etx after
(`0x01`/`0x02`, in the Cherry command set `0x81`/`0x82`; no payload).

### Header

`0x06`, offset `p*0x40 + 1`, 8 bytes (`0x5ca490`):

| Byte | Content |
|---|---|
| 0 | effect id from the device's mapping table; `+0x40` for the audio-reactive overlay |
| 1 | brightness, 0-4 |
| 2 | delay, 0-4 (the vendor UI shows it inverted as "speed") |
| 3 | direction: right 0, left 1, down 2, up 3, clockwise 6, counterclockwise 7, inward 8, outward 9 |
| 4 | random colours: 0 or 1 |
| 5-7 | R, G, B |

The software reads the header (`0x05`, same offset, 8 bytes) only when the
keyboard reports a change, and then takes effect, brightness, delay and
direction from it, never the colour.

### Lights off

`0x06`, offset `p*0x40 + lightingsEnabledOffset` (default `0x15`), 1 byte:
0 = lights on, 1 = lights off. Only on devices with `hasLightingsEnabled`
(the default).

### Effect ids

The device config key `mappingTable` selects the table.

- **Regular** (most keyboards): Wave 0x00, Spectrum 0x01, Breathing 0x02,
  Static 0x03, Radar 0x04, Vortex 0x05, Fire 0x06, Stars 0x07, Custom 0x08,
  SineWave 0x09, Rolling 0x0A, Rain 0x0B, Curve 0x0C, RedHotMetal 0x0D,
  WaveMid 0x0E, Scan 0x0F, Radiation 0x12, Ripples 0x13, SingleKey 0x15,
  XAGA 0x16, Lightning 0x17, Flame 0x18.
- **RegularCherry** (MX Board 10.1, MX Board 8.3 TKL, Pixiu 98): Radiation
  0x00, Ripples 0x01, SingleKey 0x02, Static 0x03, Custom 0x04, Rainbow 0x05,
  Wave 0x06, Spectrum 0x07, Breathing 0x08, Rolling 0x09, Curve 0x0A,
  Scan 0x0B.
- **Reduced** (MC 2.1 / MC 3.1 mice): Spectrum 0x00, Breathing 0x01,
  Static 0x02.
- **Side** (MX Board 3.1 side lighting): Wave 0x00, Spectrum 0x01,
  Breathing 0x02, SingleKey 0x03, Ripples 0x04, Static 0x05.
- **ExtendedCherry** (MX Board 3.0S Pro): FlowingLight 0x00, Spectrum 0x01,
  Breathing 0x02, Static 0x03, Custom 0x08, Neon 0x0A, Flow 0x0C,
  Radiant 0x12, WaterRipple 0x13, Shadow 0x15, StarDots 0x20, Layers 0x21,
  SineWave 0x22, ColorSpring 0x23, SilentSnow 0x24, Loop 0x25,
  ColorGrid 0x26, Snowfall 0x27, Meteor 0x28.

The Regular ids agree with the independent implementation at
<https://github.com/luv4bytes/cherrymxboard30s-rgb>.

### Per-key colours

Command CustomColorsWrite (`0x0B`, Cherry set `0x8B`), offset
`p * customLightingsOffset`, always 378 bytes: 126 entries of R, G, B. An
entry's position is the key's `keyIndex` from the vendor's layout file. With
64-byte reports that is 7 packets (6 × 56 + 42 bytes) at increasing offsets.
The effect must be Custom for the colours to show. They are never read back.

Devices with `supportsIndexTable` (K63W Pro) first read a 126-byte index
table with command `0x9B` that remaps positions.

## Keyboard performance (`KeyboardPerformance_Evision`)

- Polling rate: `0x06`, 1 byte, the index into the device's
  `pollingRatesWired` list at offset `p*0x40 + 0x35`, or into
  `pollingRatesDongle` at `p*0x40 + 0x36`. Never read back.
- Key locks: `0x06` in a write session, offset `p*0x40 + 0x16`, 1 byte.
  Bits: Win 0x01, Alt+Tab 0x02, Alt+F4 0x04, Fn+Alt+F4 0x08, Ctrl+Esc 0x10,
  Ctrl+Alt+Del 0x20, Menu 0x40, Alt+Esc 0x80. Bit 0 is also the master
  switch: without it the software writes 0. Readable with `0x05`.

## MC 2.1 / MC 3.1 mice (`MousePerformance_Evision`)

One 10-byte record at offset `0x0E`, written whole with `0x06`:

| Byte | Content |
|---|---|
| 0 | polling rate index into `[125, 250, 500, 1000]` |
| 1, 3, 5, 7 | encoded DPI of slots 1-4 |
| 2, 4, 6, 8 | 0 |
| 9 | selected slot, from 0 |

DPI encoding by the device's `dpiFormula` (`0x56e440`):

| Formula | Devices | below 5000 | from 5000 |
|---|---|---|---|
| Evision_V1 | MC 3.1 | `dpi/50 - 1` | `dpi/100 + 0x31` |
| Evision_V2 | MC 2.1, MC 3.1 (new) | `dpi/100 - 2` | `dpi/200 + 0x17` |
| Xtrfy | | `dpi/100` | same |
| Cherry | Stream Ultimate Mouse | `(dpi-1)/100` | same |

## Not analysed yet

Device matching and transports for these devices, battery, sleep timer, key
mapping and macros, pairing, displays, SOCD, Mod-Tap, the Xtrfy protocol
(M50 mouse), firmware updates.
