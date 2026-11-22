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
