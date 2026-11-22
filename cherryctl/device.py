"""Access to the mouse's vendor HID interface through hidraw."""
import glob
import os
import select
import time

from . import protocol

VENDOR_ID = 0x046A
PRODUCT_ID = 0x0402  # Stream Ultimate Mouse, connected by cable
# Report descriptor prefix of the vendor interface: usage page 0xFF1C, usage 0x92.
VENDOR_USAGE = bytes.fromhex("061cff0992")
TIMEOUT = 1.5


def find():
    """Return the hidraw path of the mouse's vendor interface, or None."""
    for sysdir in sorted(glob.glob("/sys/class/hidraw/hidraw*")):
        try:
            with open(os.path.join(sysdir, "device/uevent")) as f:
                uevent = f.read()
            with open(os.path.join(sysdir, "device/report_descriptor"), "rb") as f:
                descriptor = f.read()
        except OSError:
            continue
        if f":{VENDOR_ID:08X}:{PRODUCT_ID:08X}" not in uevent.upper():
            continue
        if VENDOR_USAGE in descriptor:
            return "/dev/" + os.path.basename(sysdir)
    return None


def usage_bytes(usage_page, usage):
    """How a vendor usage page and usage start a report descriptor collection."""
    return bytes([0x06, usage_page & 0xFF, usage_page >> 8, 0x09, usage])


def usb_version(sysdir):
    """bcdDevice of the USB device behind a hidraw sysfs directory, or None."""
    path = os.path.realpath(os.path.join(sysdir, "device"))
    while path != "/":
        try:
            with open(os.path.join(path, "bcdDevice")) as f:
                return int(f.read().strip(), 16)
        except (OSError, ValueError):
            path = os.path.dirname(path)
    return None


def scan(table):
    """Yield (hidraw path, table entry) for every connected device in table."""
    for sysdir in sorted(glob.glob("/sys/class/hidraw/hidraw*")):
        try:
            with open(os.path.join(sysdir, "device/uevent")) as f:
                uevent = f.read().upper()
            with open(os.path.join(sysdir, "device/report_descriptor"), "rb") as f:
                descriptor = f.read()
        except OSError:
            continue
        version = usb_version(sysdir)
        for info in table:
            if f":{info['vid']:08X}:{info['pid']:08X}" not in uevent:
                continue
            if usage_bytes(info["usage_page"], info["usage"]) not in descriptor:
                continue
            low, high = info.get("version_min"), info.get("version_max")
            if version is not None and ((low is not None and version < low) or (high is not None and version > high)):
                continue
            yield "/dev/" + os.path.basename(sysdir), info
            break


class Link:
    """Sends requests to a hidraw node and waits for the matching reply."""

    def __init__(self, path):
        self.fd = os.open(path, os.O_RDWR)

    def close(self):
        os.close(self.fd)

    def transfer(self, request, size=protocol.BUFFER_SIZE, verify_checksum=True, match_offset_high=True):
        os.write(self.fd, request + bytes(size - len(request)))
        deadline = time.monotonic() + TIMEOUT
        while (left := deadline - time.monotonic()) > 0:
            if not select.select([self.fd], [], [], left)[0]:
                break
            reply = os.read(self.fd, protocol.BUFFER_SIZE)
            # The same hidraw node can deliver other reports (mouse movement,
            # key events); only report 4 with our command is the reply.
            if len(reply) >= protocol.HEADER_SIZE and reply[0] == protocol.REPORT_ID and reply[3] == request[3]:
                return protocol.parse_reply(request, reply, verify_checksum, match_offset_high)
        raise protocol.ProtocolError("no reply from device")


class Mouse(Link):
    def read_table(self, offset, size=1):
        return self.transfer(protocol.read_request(protocol.CMD_TABLE_READ, size, offset))

    def write(self, cmd, payload, offset=0):
        self.transfer(protocol.write_request(cmd, payload, offset))
