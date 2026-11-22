"""A simulated mouse for trying the GUI and for tests."""
from . import protocol


class FakeMouse:
    def __init__(self):
        self.table = bytearray(0x40)
        self.dpi_table = bytes(8)
        self.presets = bytearray(protocol.HAPTICS_PRESETS * protocol.HAPTICS_PRESET_SIZE)
        self.requests = []

    def close(self):
        pass

    def transfer(self, request):
        self.requests.append(request)
        cmd, size = request[3], request[4]
        offset = request[5] | request[6] << 8
        payload = request[protocol.HEADER_SIZE :]
        reply = b""
        if cmd == protocol.CMD_TABLE_READ:
            reply = bytes(self.table[offset : offset + size])
        elif cmd == protocol.CMD_TABLE_WRITE:
            self.table[offset : offset + size] = payload
        elif cmd == protocol.CMD_DPI_TABLE_WRITE:
            self.dpi_table = payload
        elif cmd == protocol.CMD_HAPTICS_PRESET_WRITE:
            self.presets[offset : offset + size] = payload
        answer = protocol.build(cmd, size, offset, reply)
        return protocol.parse_reply(request, protocol.pad(answer))

    def read_table(self, offset, size=1):
        return self.transfer(protocol.read_request(protocol.CMD_TABLE_READ, size, offset))

    def write(self, cmd, payload, offset=0):
        self.transfer(protocol.write_request(cmd, payload, offset))


class FakeLink:
    """A simulated Evision keyboard or mouse; answers like the request's framing."""

    def __init__(self, checksum=False):
        self.checksum = checksum
        self.table = bytearray(0x100)
        self.colours = bytearray(0x600)
        self.battery = bytes([80, 1, 0])
        self.requests = []

    def close(self):
        pass

    def transfer(self, request, size=protocol.BUFFER_SIZE, verify_checksum=True, match_offset_high=True):
        self.requests.append(request)
        cmd, length = request[3], request[4]
        offset = request[5] | request[6] << 8
        payload = request[protocol.HEADER_SIZE :]
        data = b""
        if cmd == protocol.CMD_TABLE_READ:
            data = bytes(self.table[offset : offset + length])
        elif cmd == protocol.CMD_TABLE_WRITE:
            self.table[offset : offset + length] = payload
        elif cmd in (0x0B, 0x8B):
            self.colours[offset : offset + length] = payload
        elif cmd in (0x1A, 0x9A):
            data = self.battery
        reply = bytearray(request[: protocol.HEADER_SIZE] + data)
        if self.checksum:
            total = sum(reply[3:]) & 0xFFFF
            reply[1:3] = bytes([total & 0xFF, total >> 8])
        reply += bytes(size - len(reply))
        return protocol.parse_reply(request, bytes(reply), verify_checksum, match_offset_high)
