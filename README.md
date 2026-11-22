# cherry-utility-linux

Reverse engineering notes and a Linux tool for devices supported by the
CHERRY Utility Software (Windows, version 3.12).

Status: the protocol of the **Stream Ultimate Mouse** (`046a:0402`) is
documented from static analysis, and `cherryctl` builds the same packets as
the Windows software. On a real mouse, `status`, `dpi-slot` and
`haptics-preset` work. **`dpi`, `hscroll` and `haptics-set` have not been
tried on a real mouse yet.**

The Stream Ultimate Keyboard and the dongle have no settings in the vendor
software, only firmware updates, which this project does not do.

## cherryctl

Needs Python 3.8 or newer, nothing else. The mouse must be connected with its
USB cable; it cannot be configured through the dongle.

```sh
sudo cp udev/70-cherry.rules /etc/udev/rules.d/
sudo udevadm control --reload && sudo udevadm trigger

python3 -m cherryctl status
python3 -m cherryctl dpi 800 1600 3200 6000     # DPI of the four slots
python3 -m cherryctl dpi-slot 2
python3 -m cherryctl hscroll off
python3 -m cherryctl haptics-preset 1
python3 -m cherryctl haptics-set 1 --mode round --distance 17 --force 40 \
    --length 14 --speed-compensation -3 --threshold 6
```

`--dry-run` prints the packets instead of sending them.

## Other CHERRY keyboards and mice (experimental)

`cherryctl` also knows 51 other devices that use the same protocol family
(MX Board, G80-3000, MX LP, K63W, Pixiu keyboards; MC 2.1 / MC 3.1 mice).
**This part comes from code analysis only and has never been run against
such a device.** See [docs/evision-devices.md](docs/evision-devices.md).

```sh
python3 -m cherryctl devices
python3 -m cherryctl lighting                      # show state and effects
python3 -m cherryctl lighting --effect Static --brightness 4 --colour ff8800
python3 -m cherryctl lighting --off
python3 -m cherryctl profile 2
python3 -m cherryctl polling-rate 1000
python3 -m cherryctl battery
```

Each device needs a udev rule like the one in `udev/70-cherry.rules` with its
own product ID. The device table `cherryctl/data/devices.json` is generated
from the vendor's definitions by `tools/gen_devices.py`.

## Settings window

Needs PySide6 (Fedora: `python3-pyside6`).

```sh
python3 -m cherryctl.gui          # the connected mouse
python3 -m cherryctl.gui --demo   # a simulated mouse, nothing is sent
```

The mouse reports only which DPI slot and haptics preset are selected. DPI
values and preset parameters cannot be read from it, so the window shows the
values last applied from this computer (stored in
`~/.config/cherryctl/stream-ultimate-mouse.json`) and writes all of them on
Apply.

Tests: `python3 -m unittest`

## Documentation

- [docs/protocol.md](docs/protocol.md): packet format, Stream Ultimate Mouse commands, open questions.
- [docs/evision-devices.md](docs/evision-devices.md): lighting, profiles and other settings of the other devices.

## Analysis tools

- `tools/rcc_extract.py` extracts a Qt resource file (`.rcc`).
- `tools/find_embedded_rcc.py` finds and extracts Qt resources compiled into
  an executable.

The vendor installer, its extracted files, the decompiler output and firmware
images are not part of this repository. They live in `work/`, which git
ignores.
