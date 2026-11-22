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


class Mouse:
    def __init__(self, path):
        self.fd = os.open(path, os.O_RDWR)

    def close(self):
        os.close(self.fd)

    def transfer(self, request):
        os.write(self.fd, protocol.pad(request))
        deadline = time.monotonic() + TIMEOUT
        while (left := deadline - time.monotonic()) > 0:
            if not select.select([self.fd], [], [], left)[0]:
                break
            reply = os.read(self.fd, protocol.BUFFER_SIZE)
            # The same hidraw node delivers mouse movement (report 1) and
            # other reports; only report 4 belongs to this protocol.
            if len(reply) >= protocol.HEADER_SIZE and reply[0] == protocol.REPORT_ID and reply[3] == request[3]:
                return protocol.parse_reply(request, reply)
        raise protocol.ProtocolError("no reply from device")

    def read_table(self, offset, size=1):
        return self.transfer(protocol.read_request(protocol.CMD_TABLE_READ, size, offset))

    def write(self, cmd, payload, offset=0):
        self.transfer(protocol.write_request(cmd, payload, offset))
