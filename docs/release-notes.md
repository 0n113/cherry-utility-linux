**CHERRY Stream Ultimate Mouse (firmware 0.21, USB cable):** works. All settings were written to a real mouse with this tool, and the packets are bit-identical to those the vendor software sends (compared against a USB capture).

**51 other keyboards and mice** (lighting, on-board profiles, polling rate, battery): built from code analysis, not yet tried on hardware. Reports are welcome, see CONTRIBUTING.md.

## Use

```sh
chmod +x cherryctl-*-x86_64.AppImage
./cherryctl-*-x86_64.AppImage              # settings window
./cherryctl-*-x86_64.AppImage status       # command line, see --help
```

Your user needs access to the device's hidraw node: install `udev/70-cherry.rules` from the repository as described in the README, then replug the device.

The AppImage bundles Python 3.12 and Qt 6 (PySide6) and needs an x86_64 Linux with glibc 2.28 or newer.
