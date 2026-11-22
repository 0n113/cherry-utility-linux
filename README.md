# cherry-utility-linux

Reverse engineering notes and Linux tooling for devices supported by the
CHERRY Utility Software (Windows, version 3.12).

Status: analysis in progress. Nothing here talks to a device yet.

The vendor installer, its extracted files and firmware images are not part of
this repository. They live in `work/`, which is ignored by git.

## Tools

- `tools/rcc_extract.py` extracts a Qt resource file (`.rcc`).
- `tools/find_embedded_rcc.py` finds and extracts Qt resources compiled into
  an executable.
