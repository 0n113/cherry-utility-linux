import unittest

from cherryctl import evision, fake, table


def device(name, checksum=None):
    info = next(d for d in table.load() if d["name"] == name)
    link = fake.FakeLink(info["checksum"] if checksum is None else checksum)
    return evision.Device(info, link), link


class LightingTest(unittest.TestCase):
    def test_header_packets(self):
        dev, link = device("MX board 3 0S")
        dev.set_lighting(effect="Static", brightness=4, delay=2, colour=(255, 0, 16))
        self.assertEqual(
            [r.hex(" ") for r in link.requests],
            [
                "04 00 00 01 00 00 00 55",  # Stx
                "04 00 00 06 08 01 00 55 03 04 02 00 00 ff 00 10",
                "04 00 00 02 00 00 00 55",  # Etx
            ],
        )

    def test_round_trip(self):
        dev, _ = device("MX board 3 0S")
        dev.set_lighting(effect="Wave", brightness=3, delay=1, direction="left")
        dev.set_lighting_on(False)
        self.assertEqual(dev.lighting(), {"effect": "Wave", "brightness": 3, "delay": 1, "direction": "left", "on": False})

    def test_rejects_effect_the_device_lacks(self):
        dev, link = device("MX board 3 0S")
        with self.assertRaises(ValueError):
            dev.set_lighting(effect="Meteor", brightness=1, delay=1)
        self.assertEqual(link.requests, [])

    def test_key_colours_are_chunked(self):
        dev, link = device("MX board 3 0S")
        dev.set_key_colours({0: (1, 2, 3), 125: (7, 8, 9)})
        writes = [r for r in link.requests if r[3] == 0x0B]
        self.assertEqual([r[4] for r in writes], [56] * 6 + [42])
        self.assertEqual([r[5] | r[6] << 8 for r in writes], [0, 56, 112, 168, 224, 280, 336])
        self.assertEqual(bytes(link.colours[0:3]), b"\x01\x02\x03")
        self.assertEqual(bytes(link.colours[375:378]), b"\x07\x08\x09")

    def test_cherry_command_set_with_checksum(self):
        dev, link = device("MX board 3 0S Pro")
        dev.set_lighting(effect="Static", brightness=1, delay=0)
        sent = [r.hex(" ") for r in link.requests]
        self.assertIn("04 81 00 81 00 00 00 00", sent)  # Stx with checksum
        self.assertEqual(sent[-1], "04 82 00 82 00 00 00 00")  # Etx


class ProfileTest(unittest.TestCase):
    def test_settings_follow_the_active_profile(self):
        name = next(d["name"] for d in table.load() if "profiles" in d["features"] and "lighting" in d["features"])
        dev, link = device(name)
        dev.set_profile(2)
        effect = dev.features["lighting"]["effects"][0]
        dev.set_lighting(effect=effect, brightness=1, delay=1)
        write = next(r for r in link.requests if r[3] == 0x06 and r[4] == 8)
        self.assertEqual(write[5] | write[6] << 8, 2 * 0x40 + 1)

    def test_profile_out_of_range(self):
        name = next(d["name"] for d in table.load() if "profiles" in d["features"])
        dev, _ = device(name)
        with self.assertRaises(ValueError):
            dev.set_profile(3)


class OtherSettingsTest(unittest.TestCase):
    def test_mouse_record(self):
        dev, _ = device("MC 3 1 Mouse")  # Evision_V1
        self.assertEqual(dev.mouse_record(500, [400, 800, 1600, 5000], 1).hex(" "), "02 07 00 0f 00 1f 00 63 00 01")

    def test_dpi_formulas(self):
        self.assertEqual(evision.encode_dpi("Evision_V2", 800), 6)
        self.assertEqual(evision.encode_dpi("Evision_V2", 8000), 0x3F)
        self.assertEqual(evision.encode_dpi("Cherry", 6000), 59)

    def test_battery(self):
        name = next(d["name"] for d in table.load() if "battery" in d["features"])
        dev, _ = device(name)
        self.assertEqual(dev.battery(), (80, True))

    def test_locks_need_win(self):
        name = next(d["name"] for d in table.load() if d["features"].get("keyboard_performance", {}).get("locks"))
        dev, link = device(name)
        locks = dev.features["keyboard_performance"]["locks"]
        other = next(lock for lock in locks if lock != "Win")
        with self.assertRaises(ValueError):
            dev.set_key_locks([other])
        dev.set_key_locks(["Win", other])
        self.assertEqual(dev.key_locks(), [lock for lock in locks if lock in ("Win", other)])

    def test_missing_feature(self):
        dev, _ = device("MX board 3 0S")
        with self.assertRaises(ValueError):
            dev.battery()


if __name__ == "__main__":
    unittest.main()
