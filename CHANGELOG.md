# Changelog

## 0.1.3

- The settings window follows DPI slot and haptics preset changes made with
  the mouse's own buttons instead of overwriting them on Apply.
- All settings of the Stream Ultimate Mouse have now been written to a real
  mouse with cherryctl.
- The AppImage build verifies its downloads against pinned checksums.
- MIT licence.

## 0.1.2

- Same as 0.1.1, whose release build failed; no AppImage exists for 0.1.1.

## 0.1.1

- Fix the DPI table of the Stream Ultimate Mouse: each slot takes two bytes.
  0.1.0 wrote slots 2 to 4 wrongly. Found by comparing with a USB capture of
  the vendor software; all packets for the mouse now match it bit for bit.

## 0.1.0

- Stream Ultimate Mouse: DPI slots, horizontal scrolling and scroll wheel
  haptics, from the command line and in a settings window.
- Experimental support for 51 other CHERRY keyboards and mice: lighting,
  on-board profiles, polling rate, battery level.
- AppImage build.
