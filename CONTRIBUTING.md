# Contributing

## Reports from real devices

Only the Stream Ultimate Mouse has been tried on hardware. For every other
device the code follows an analysis of the vendor software and may be wrong.
If you own one of them, a report of what works and what does not is the most
useful contribution; please use the "Device report" issue template.

Try reading before writing: `cherryctl devices`, `cherryctl lighting`,
`cherryctl battery` and `cherryctl profile` only read.

## Code

- `python3 -m unittest` must pass. Tests need neither a device nor PySide6;
  `cherryctl/fake.py` has simulated devices.
- A packet layout that was confirmed against the vendor software belongs in a
  test (see `tests/test_vendor_capture.py`).
- State in the docs how each fact is known: observed on a device, captured
  from the vendor software, or read from its code.

## What stays out of the repository

No files from the vendor's software: no installer contents, firmware images,
pictures, layout files or decompiler output. `cherryctl/data/devices.json` is
generated from the vendor's device definitions by `tools/gen_devices.py` and
holds only identifiers and parameters cherryctl needs.
