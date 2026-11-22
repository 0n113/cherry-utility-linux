"""Configure a CHERRY Stream Ultimate Mouse connected by USB cable.

    python3 -m cherryctl status
    python3 -m cherryctl dpi 800 1600 3200 6000
    python3 -m cherryctl dpi-slot 2
    python3 -m cherryctl hscroll on
    python3 -m cherryctl haptics-preset 1
    python3 -m cherryctl haptics-set 0 --mode round --distance 17 --force 40 \\
        --length 14 --speed-compensation -3 --threshold 6

With --dry-run the packets are printed instead of sent.

Other CHERRY keyboards and mice (experimental, untested on hardware):

    python3 -m cherryctl devices
    python3 -m cherryctl lighting
    python3 -m cherryctl lighting --effect Static --brightness 4 --colour ff8800
    python3 -m cherryctl lighting --off
    python3 -m cherryctl profile 2
    python3 -m cherryctl polling-rate 1000
    python3 -m cherryctl battery
"""
import argparse
import sys

from . import device, evision, protocol, table


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


def open_evision(args):
    found = list(device.scan(table.load()))
    if args.device:
        found = [(path, info) for path, info in found if path == args.device]
    if not found:
        sys.exit("no supported keyboard or mouse found")
    if len(found) > 1:
        names = ", ".join(f"{info['name']} ({path})" for path, info in found)
        sys.exit(f"several devices found, choose one with --device: {names}")
    path, info = found[0]
    try:
        return evision.Device(info, device.Link(path))
    except PermissionError:
        sys.exit(f"no permission for {path}; see README for the udev rule")


def cmd_devices(args):
    path = device.find()
    if path:
        print(f"{path}  Stream Ultimate Mouse")
    for path, info in device.scan(table.load()):
        print(f"{path}  {info['name']}  ({', '.join(sorted(info['features'])).replace('_', ' ')})")


def parse_colour(text):
    text = text.lstrip("#")
    if len(text) != 6:
        raise argparse.ArgumentTypeError("colour must be RRGGBB")
    try:
        return tuple(bytes.fromhex(text))
    except ValueError:
        raise argparse.ArgumentTypeError("colour must be RRGGBB") from None


def cmd_lighting(args):
    dev = open_evision(args)
    try:
        if args.on is not None:
            dev.set_lighting_on(args.on)
        if args.effect:
            config = dev.need("lighting")
            dev.set_lighting(
                effect=args.effect,
                brightness=config["brightness"][1] if args.brightness is None else args.brightness,
                delay=config["delay"][0] if args.speed is None else config["delay"][1] - args.speed,
                direction=args.direction, random=args.random, colour=args.colour,
            )
        elif args.on is None:
            state = dev.lighting()
            config = dev.need("lighting")
            print(f"effects: {', '.join(sorted(config['effects']))}")
            print(f"effect: {state['effect']}")
            print(f"brightness: {state['brightness']} (of {config['brightness'][1]})")
            print(f"speed: {config['delay'][1] - state['delay']} (of {config['delay'][1]})")
            if "on" in state:
                print(f"lighting: {'on' if state['on'] else 'off'}")
    finally:
        dev.close()


def cmd_profile(args):
    dev = open_evision(args)
    try:
        if args.profile is None:
            dev.need("profiles")
            print(f"profile: {dev.profile() + 1}")
        else:
            dev.set_profile(args.profile - 1)
    finally:
        dev.close()


def cmd_polling_rate(args):
    dev = open_evision(args)
    try:
        dev.set_polling_rate(args.rate, dongle=args.dongle)
    finally:
        dev.close()


def cmd_battery(args):
    dev = open_evision(args)
    try:
        level, charging = dev.battery()
        print(f"battery: {level} %{', charging' if charging else ''}")
    finally:
        dev.close()


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

    sub.add_parser("devices", help="list connected supported devices").set_defaults(run=cmd_devices)

    p = sub.add_parser("lighting", help="show or set keyboard lighting (experimental)")
    p.add_argument("--effect")
    p.add_argument("--brightness", type=int)
    p.add_argument("--speed", type=int)
    p.add_argument("--direction", default="right", choices=sorted(evision.DIRECTIONS))
    p.add_argument("--random", action="store_true", help="random colours")
    p.add_argument("--colour", "--color", type=parse_colour, default=(255, 255, 255), metavar="RRGGBB")
    p.add_argument("--on", dest="on", action="store_true", default=None)
    p.add_argument("--off", dest="on", action="store_false")
    p.set_defaults(run=cmd_lighting)

    p = sub.add_parser("profile", help="show or switch the on-board profile (experimental)")
    p.add_argument("profile", type=int, nargs="?")
    p.set_defaults(run=cmd_profile)

    p = sub.add_parser("polling-rate", help="set a keyboard's polling rate in Hz (experimental)")
    p.add_argument("rate", type=int)
    p.add_argument("--dongle", action="store_true", help="the rate used through the dongle")
    p.set_defaults(run=cmd_polling_rate)

    sub.add_parser("battery", help="show the battery level (experimental)").set_defaults(run=cmd_battery)

    args = ap.parse_args()
    if hasattr(args, "run"):
        try:
            args.run(args)
        except (ValueError, protocol.ProtocolError) as err:
            sys.exit(f"error: {err}")
        return
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
