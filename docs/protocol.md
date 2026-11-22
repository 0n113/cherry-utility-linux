# Protocol notes

Source: static analysis of `cus.exe` from CHERRY Utility Software 3.12
(SHA-256 `4c842b59…618108`), decompiled with Ghidra 12.2, and the device
definitions in its Qt resources. Function addresses below refer to that
binary.

**Nothing here has been confirmed against a device yet.** The packets are
what the Windows software builds; how the firmware reacts is not known.

## Devices of the Stream Desktop Ultimate set

| Device | USB ID | What the vendor software offers |
|---|---|---|
| Stream Ultimate Keyboard | `046a:0401` | firmware update only |
| Stream Ultimate Dongle | `046a:0400` | firmware update only |
| Stream Ultimate Mouse | `046a:0402` | DPI slots, horizontal scroll, scroll wheel haptics, firmware update |

The mouse is configured through its USB cable. Behind the dongle the software
only shows "use USB cable for configuration".

## Transport

The mouse definition names three HID interfaces. Configuration uses
`usb-endpoint-cherry`: usage page `0xFF1C`, usage `0x92`, 64-byte reports.

The software sends each request with `hid_write` as an output report, padded
with zeros to 64 bytes (`0x617520`). Replies are read from the same interface
with a timeout of 1500 ms per request; one request is in flight at a time.

## Packet

Built by `0x60a860`:

| Offset | Size | Content |
|---|---|---|
| 0 | 1 | `0x04`, the HID report ID |
| 1 | 2 | checksum, little endian: sum of all bytes from offset 3 to the end of the payload |
| 3 | 1 | command |
| 4 | 1 | size: payload length for a write, number of bytes wanted for a read |
| 5 | 2 | offset, little endian |
| 7 | 1 | offset bits 16-23 |
| 8 | n | payload (writes only), at most 56 bytes |

A reply has the same header. The software accepts it when command, size and
offset equal those of the request (`0x60a9a0`) and takes `size` bytes from
offset 8 as data. It does not check the reply's first three bytes, so whether
the device sends a checksum back is unknown.

This is the framing of the Evision protocol used by other CHERRY keyboards.
The "Cherry" command set differs only in some command numbers
(`0x6114f0` versus `0x611760`), for example start/end of a write session
`0x81`/`0x82` instead of `0x01`/`0x02`. The mouse features below do not use
write sessions.

## Mouse settings (`MousePerformance_Cherry`)

| Setting | Command | Offset | Payload |
|---|---|---|---|
| read selected DPI slot | `0x05` | `0x16` | reply: 1 byte, slot index from 0 |
| select DPI slot | `0x06` | `0x16` | 1 byte, slot index from 0 |
| horizontal scroll | `0x06` | `0x26` | 1 byte, 0 or 1 |
| DPI values | `0x7F` | 0 | 8 bytes: one per slot, then 4 zero bytes |

A DPI value is encoded as `(dpi - 1) / 100` (`0x4fb1c0`): 200 is 1, 1000 is
9, 6000 is 59. Allowed are 200 to 6000 in steps of 100.

The software never reads DPI values or the scroll setting from the mouse. It
keeps them in its own profile (defaults 1000/2000/3000/4000, slot 1,
horizontal scroll on) and writes all three settings when the mouse connects.

Polling rate and debounce time are not implemented for this mouse.

## Scroll wheel haptics (`Haptics_Evision`)

| Setting | Command | Offset | Payload |
|---|---|---|---|
| read selected preset | `0x05` | `0x17` | reply: 1 byte, preset index from 0 |
| select preset | `0x06` | `0x17` | 1 byte, preset index from 0 |
| write preset *i* | `0x7D` | `7 * i` | 7 bytes, see below |

Preset record (`0x53e130`):

| Byte | Field | Values |
|---|---|---|
| 0 | tick mode | 2 = round, 1 = sharp |
| 1 | tick distance | 1-36 |
| 2 | tick force | 0-100 |
| 3 | tick length | 1-50 |
| 4 | speed compensation | -10 to 10 as a signed byte |
| 5 | free-wheeling | 0 or 1 |
| 6 | free-wheeling threshold | 1-10 |

There are 4 presets. The software never reads a preset back; it keeps them in
its profile and writes all of them when the mouse connects.

Vendor defaults:

| Preset | Mode | Distance | Force | Length | Speed comp. | Free-wheeling | Threshold |
|---|---|---|---|---|---|---|---|
| Basic | round | 17 | 40 | 14 | -3 | off | 6 |
| Smooth | sharp | 10 | 24 | 13 | 0 | on | 6 |
| Precision | round | 7 | 40 | 14 | 3 | off | 6 |
| Control | sharp | 13 | 40 | 20 | 0 | off | 6 |

## Firmware update (not implemented here)

Keyboard, dongle and mouse use a Nordic bootloader. The software writes one
8-byte report on the interface with usage page `0xFFA0` (report ID 9) —
`09 84 57 00 00 F3 00 00`, for the mouse `09 09 84 57 00 00 F3 00`
(`0x5835b0`) — and then talks to a serial-port bootloader. That this report
is the switch into the bootloader is an inference.

## Open questions

- Does the firmware answer as the software expects? Needs a mouse on a cable.
- Is the HID output report on usage page `0xFF1C` really report ID 4 with 63
  data bytes? Check the report descriptor of `046a:0402`.
- Can DPI values and haptics presets be read from the mouse at all?
- Where does the software get the mouse's firmware version from?
- What do the unsolicited reports on this interface contain (the software
  reloads the DPI slot when the mouse reports a change)?

## Other devices

The software supports about 60 devices with further features (lighting, key
mapping, macros, profiles, battery, pairing) on the same framing. They are
not analysed here. For lighting on the MX Board 3.0S see
<https://github.com/luv4bytes/cherrymxboard30s-rgb>.
