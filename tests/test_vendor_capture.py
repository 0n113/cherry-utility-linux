"""Compare our packets with a capture of the vendor software.

The packets below were sent by CHERRY Utility Software 3.12 to a Stream
Ultimate Mouse (firmware 0.21) when it connected with its default profile,
captured on the USB bus on 2026-11-22. Each was 64 bytes long, zero-padded.
"""
import unittest

from cherryctl import fake, protocol, settings

VENDOR_PACKETS = [
    "04 e7 00 7f 08 00 00 00 09 00 13 00 1d 00 27 00",  # DPI 1000/2000/3000/4000
    "04 1d 00 06 01 16 00 00 00",  # DPI slot 1
    "04 2e 00 06 01 26 00 00 01",  # horizontal scrolling on
    "04 d0 01 7d 07 00 00 00 02 11 28 0e fd 00 06",  # preset Basic
    "04 c2 00 7d 07 07 00 00 01 0a 18 0d 00 01 06",  # preset Smooth
    "04 da 00 7d 07 0e 00 00 02 07 28 0e 03 00 06",  # preset Precision
    "04 e9 00 7d 07 15 00 00 01 0d 28 14 00 00 06",  # preset Control
    "04 1e 00 06 01 17 00 00 00",  # haptics preset 1
]


class VendorCaptureTest(unittest.TestCase):
    def test_default_profile_is_bit_identical(self):
        mouse = fake.FakeMouse()
        settings.apply(mouse, settings.defaults())
        ours = [protocol.pad(request) for request in mouse.requests]
        vendor = [protocol.pad(bytes.fromhex(packet)) for packet in VENDOR_PACKETS]
        self.assertEqual(ours, vendor)


if __name__ == "__main__":
    unittest.main()
