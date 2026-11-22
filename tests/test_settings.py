import os
import tempfile
import unittest

from cherryctl import fake, protocol, settings


class ApplyTest(unittest.TestCase):
    def test_apply_writes_everything(self):
        mouse = fake.FakeMouse()
        s = settings.defaults()
        s["dpi_slot"], s["haptics_preset"], s["horizontal_scroll"] = 2, 3, False
        settings.apply(mouse, s)
        self.assertEqual(mouse.dpi_table.hex(" "), "09 00 13 00 1d 00 27 00")
        self.assertEqual(mouse.table[protocol.OFFSET_DPI_SLOT], 2)
        self.assertEqual(mouse.table[protocol.OFFSET_HAPTICS_PRESET], 3)
        self.assertEqual(mouse.table[protocol.OFFSET_HORIZONTAL_SCROLL], 0)
        self.assertEqual(bytes(mouse.presets[7:14]).hex(" "), "01 0a 18 0d 00 01 06")

    def test_invalid_settings_send_nothing(self):
        mouse = fake.FakeMouse()
        s = settings.defaults()
        s["dpis"][3] = 9000
        with self.assertRaises(ValueError):
            settings.apply(mouse, s)
        self.assertEqual(mouse.requests, [])

    def test_read_selection(self):
        mouse = fake.FakeMouse()
        mouse.table[protocol.OFFSET_DPI_SLOT] = 1
        mouse.table[protocol.OFFSET_HAPTICS_PRESET] = 9  # out of range: keep ours
        s = settings.defaults()
        settings.read_selection(mouse, s)
        self.assertEqual((s["dpi_slot"], s["haptics_preset"]), (1, 0))


class StoreTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.old = os.environ.get("XDG_CONFIG_HOME")
        os.environ["XDG_CONFIG_HOME"] = self.dir.name
        self.addCleanup(self.restore)

    def restore(self):
        if self.old is None:
            del os.environ["XDG_CONFIG_HOME"]
        else:
            os.environ["XDG_CONFIG_HOME"] = self.old

    def test_round_trip(self):
        s = settings.defaults()
        s["dpis"] = [400, 800, 1600, 3200]
        settings.save(s)
        self.assertEqual(settings.load(), s)

    def test_unusable_file_gives_defaults(self):
        os.makedirs(os.path.dirname(settings.path()))
        with open(settings.path(), "w") as f:
            f.write('{"dpis": [1, 2]}')
        self.assertEqual(settings.load(), settings.defaults())


if __name__ == "__main__":
    unittest.main()
