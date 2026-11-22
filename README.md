# cherryctl

Configure CHERRY keyboards and mice on Linux. The protocol was reverse
engineered from the CHERRY Utility Software for Windows (version 3.12); this
project is not affiliated with CHERRY.

## What works

| Device | State |
|---|---|
| Stream Ultimate Mouse (`046a:0402`, USB cable) | All packets are bit-identical to those of the vendor software (compared with a USB capture, firmware 0.21). Reading and switching the DPI slot and the haptics preset were tried with `cherryctl` on a real mouse; writing DPI values, preset parameters and horizontal scrolling was not yet. |
| 51 other keyboards and mice (MX Board, G80-3000, MX LP, K63W, Pixiu; MC 2.1 / MC 3.1) | **Experimental.** Lighting, on-board profiles, polling rate and battery level, built from code analysis only and never run against such a device. |
| Stream Ultimate Keyboard and its dongle | Nothing to configure: the vendor software only offers firmware updates for them, which this project does not do. |

The Stream Ultimate Mouse can only be configured through its USB cable, not
through the dongle.

## Install

### AppImage

Download `cherryctl-*-x86_64.AppImage` from the
[releases](https://github.com/0n113/cherry-utility-linux/releases), then:

```sh
chmod +x cherryctl-*-x86_64.AppImage
./cherryctl-*-x86_64.AppImage              # settings window
./cherryctl-*-x86_64.AppImage status       # command line
```

### From a checkout

Needs Python 3.8 or newer; the settings window also needs PySide6.

```sh
pip install ".[gui]"      # or: pip install .   for the command line only
cherryctl --help
```

Without installing, `python3 -m cherryctl` in the checkout does the same.

### Device access

Your user needs access to the device's hidraw node. Install the udev rules
once, then replug the device:

```sh
sudo cp udev/70-cherry.rules /etc/udev/rules.d/
sudo udevadm control --reload
```

## Command line

Stream Ultimate Mouse:

```sh
cherryctl status
cherryctl dpi 800 1600 3200 6000     # DPI of the four slots
cherryctl dpi-slot 2
cherryctl hscroll off
cherryctl haptics-preset 1
cherryctl haptics-set 1 --mode round --distance 17 --force 40 \
    --length 14 --speed-compensation -3 --threshold 6
```

With `--dry-run` these commands print their packets instead of sending them.

Other devices (experimental):

```sh
cherryctl devices
cherryctl lighting                      # show state and available effects
cherryctl lighting --effect Static --brightness 4 --colour ff8800
cherryctl lighting --off
cherryctl profile 2
cherryctl polling-rate 1000
cherryctl battery
```

## Settings window

```sh
cherryctl gui
cherryctl gui --demo                           # simulated mouse, nothing is sent
cherryctl gui --demo-device "MX board 3 0S"    # simulated keyboard
```

The mouse reports only which DPI slot and haptics preset are selected. DPI
values and preset parameters cannot be read from it, so the window shows the
values last applied from this computer (stored in
`~/.config/cherryctl/stream-ultimate-mouse.json`, at first the vendor's
defaults) and writes all of them on Apply.

Without a Stream Ultimate Mouse, the window opens for the first other
supported device it finds.

## Documentation

- [docs/protocol.md](docs/protocol.md): packet format, Stream Ultimate Mouse
  commands, open questions.
- [docs/evision-devices.md](docs/evision-devices.md): lighting, profiles and
  other settings of the other devices.
- [CHANGELOG.md](CHANGELOG.md)

## Development

```sh
python3 -m unittest             # tests; they need no device and no PySide6
packaging/appimage/build.sh     # builds dist/cherryctl-VERSION-x86_64.AppImage
```

Pushing a tag `vX.Y.Z` that matches `cherryctl/__init__.py` builds the
AppImage on GitHub and publishes it as a release.

Layout:

- `cherryctl/` — the tool: `protocol.py` (packets), `device.py` (hidraw),
  `settings.py` (stored mouse settings), `evision.py` (other devices),
  `gui.py` and `gui_evision.py` (windows), `fake.py` (simulated devices),
  `data/devices.json` (device table).
- `tools/` — analysis helpers: `rcc_extract.py` and `find_embedded_rcc.py`
  extract Qt resources from `.rcc` files and executables;
  `gen_devices.py` builds the device table and the udev rules from the
  vendor's device definitions.

The vendor installer, its extracted files, the decompiler output and firmware
images are not part of this repository. They live in `work/`, which git
ignores.
