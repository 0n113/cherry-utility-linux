import contextlib
import io
import sys
import unittest

from cherryctl import __main__ as cli


def run(*argv):
    """Run the command line; return (exit status or None, stdout)."""
    out = io.StringIO()
    old = sys.argv
    sys.argv = ["cherryctl", *argv]
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            try:
                cli.main()
                return None, out.getvalue()
            except SystemExit as err:
                return err.code, out.getvalue()
    finally:
        sys.argv = old


class DryRunTest(unittest.TestCase):
    def test_prints_mouse_packets(self):
        status, out = run("--dry-run", "dpi", "800", "1600", "3200", "6000")
        self.assertIsNone(status)
        self.assertEqual(out.strip(), "04 f7 00 7f 08 00 00 00 07 0f 1f 3b 00 00 00 00")

    def test_refused_for_other_devices(self):
        status, _ = run("--dry-run", "lighting", "--effect", "Static")
        self.assertIn("--dry-run only works", status)

    def test_slot_out_of_range(self):
        status, _ = run("--dry-run", "dpi-slot", "5")
        self.assertEqual(status, 2)


class LightingArgumentsTest(unittest.TestCase):
    def test_settings_need_an_effect(self):
        status, _ = run("lighting", "--brightness", "2")
        self.assertIn("--effect", status)


if __name__ == "__main__":
    unittest.main()
