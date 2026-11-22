"""Configure a CHERRY Stream Ultimate Mouse connected by USB cable.

    python3 -m cherryctl status
    python3 -m cherryctl dpi 800 1600 3200 6000
    python3 -m cherryctl dpi-slot 2
    python3 -m cherryctl hscroll on
    python3 -m cherryctl haptics-preset 1
    python3 -m cherryctl haptics-set 0 --mode round --distance 17 --force 40 \\
        --length 14 --speed-compensation -3 --threshold 6

With --dry-run the packets are printed instead of sent.
"""
import argparse
import sys

from . import device, protocol


class DryRun:
    """Prints requests instead of sending them."""

    def read_table(self, offset, size=1):
        print(protocol.read_request(protocol.CMD_TABLE_READ, size, offset).hex(" "))
        return None

    def write(self, cmd, payload, offset=0):
        print(protocol.write_request(cmd, payload, offset).hex(" "))

    def close(self):
        pass


def cmd_status(mouse, args):
    slot = mouse.read_table(protocol.OFFSET_DPI_SLOT)
    preset = mouse.read_table(protocol.OFFSET_HAPTICS_PRESET)
    if slot is not None:
        print(f"DPI slot: {slot[0] + 1}")
        print(f"haptics preset: {preset[0] + 1}")


def cmd_dpi(mouse, args):
    mouse.write(protocol.CMD_DPI_TABLE_WRITE, protocol.dpi_table(args.dpi))


def slot_number(count):
    def parse(text):
        value = int(text)
        if not 1 <= value <= count:
            raise argparse.ArgumentTypeError(f"must be 1..{count}")
        return value - 1

    return parse


def cmd_dpi_slot(mouse, args):
    mouse.write(protocol.CMD_TABLE_WRITE, bytes([args.slot]), protocol.OFFSET_DPI_SLOT)


def cmd_hscroll(mouse, args):
    mouse.write(protocol.CMD_TABLE_WRITE, bytes([args.state == "on"]), protocol.OFFSET_HORIZONTAL_SCROLL)


def cmd_haptics_preset(mouse, args):
    mouse.write(protocol.CMD_TABLE_WRITE, bytes([args.preset]), protocol.OFFSET_HAPTICS_PRESET)


def cmd_haptics_set(mouse, args):
    record = protocol.haptics_preset(
        args.mode, args.distance, args.force, args.length, args.speed_compensation, args.free_wheeling, args.threshold
    )
    mouse.write(protocol.CMD_HAPTICS_PRESET_WRITE, record, args.preset * protocol.HAPTICS_PRESET_SIZE)


def main():
    ap = argparse.ArgumentParser(prog="cherryctl", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="print packets instead of sending them")
    ap.add_argument("--device", help="hidraw path (default: find the mouse)")
    sub = ap.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="show the selected DPI slot and haptics preset").set_defaults(func=cmd_status)

    p = sub.add_parser("dpi", help="set the DPI values of the four slots")
    p.add_argument("dpi", type=int, nargs=protocol.DPI_SLOTS)
    p.set_defaults(func=cmd_dpi)

    p = sub.add_parser("dpi-slot", help="select a DPI slot (1-4)")
    p.add_argument("slot", type=slot_number(protocol.DPI_SLOTS))
    p.set_defaults(func=cmd_dpi_slot)

    p = sub.add_parser("hscroll", help="turn horizontal scrolling on or off")
    p.add_argument("state", choices=["on", "off"])
    p.set_defaults(func=cmd_hscroll)

    p = sub.add_parser("haptics-preset", help="select a scroll wheel haptics preset (1-4)")
    p.add_argument("preset", type=slot_number(protocol.HAPTICS_PRESETS))
    p.set_defaults(func=cmd_haptics_preset)

    p = sub.add_parser("haptics-set", help="write the parameters of a haptics preset (1-4)")
    p.add_argument("preset", type=slot_number(protocol.HAPTICS_PRESETS))
    p.add_argument("--mode", choices=sorted(protocol.TICK_MODES), required=True)
    p.add_argument("--distance", type=int, required=True, help="tick distance, 1-36")
    p.add_argument("--force", type=int, required=True, help="tick force, 0-100")
    p.add_argument("--length", type=int, required=True, help="tick length, 1-50")
    p.add_argument("--speed-compensation", type=int, default=0, help="-10 to 10")
    p.add_argument("--free-wheeling", action="store_true")
    p.add_argument("--threshold", type=int, default=6, help="free-wheeling threshold, 1-10")
    p.set_defaults(func=cmd_haptics_set)

    args = ap.parse_args()
    if args.dry_run:
        mouse = DryRun()
    else:
        path = args.device or device.find()
        if not path:
            sys.exit("Stream Ultimate Mouse not found. Connect it with the USB cable; it cannot be configured through the dongle.")
        try:
            mouse = device.Mouse(path)
        except PermissionError:
            sys.exit(f"no permission for {path}; install udev/70-cherry.rules (see README)")
    try:
        args.func(mouse, args)
    except (ValueError, protocol.ProtocolError) as err:
        sys.exit(f"error: {err}")
    finally:
        mouse.close()


if __name__ == "__main__":
    main()
