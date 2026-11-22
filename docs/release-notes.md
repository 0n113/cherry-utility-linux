**Do not use 0.1.0 to set DPI values:** it wrote the DPI table of the Stream Ultimate Mouse wrongly (slots 2 to 4). This release fixes that.

**CHERRY Stream Ultimate Mouse (firmware 0.21, USB cable):** the packets for all settings are bit-identical to those the vendor software sends (compared against a USB capture). Reading and switching the DPI slot and haptics preset were tried with this tool on a real mouse; writing DPI values, preset parameters and horizontal scrolling was not.

**51 other keyboards and mice** (lighting, on-board profiles, polling rate, battery): built from code analysis, not yet tried on hardware.

## Use

```sh
chmod +x cherryctl-*-x86_64.AppImage
./cherryctl-*-x86_64.AppImage              # settings window
./cherryctl-*-x86_64.AppImage status       # command line, see --help
```

Your user needs access to the device's hidraw node: install `udev/70-cherry.rules` from the repository as described in the README, then replug the device.

The AppImage bundles Python 3.12 and Qt 6 (PySide6) and needs an x86_64 Linux with glibc 2.28 or newer.
