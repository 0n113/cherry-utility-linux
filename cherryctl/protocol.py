"""Packet format of the "Cherry" command set (a variant of the Evision protocol).

Derived from static analysis of cus.exe 3.12; see docs/protocol.md.
"""

REPORT_ID = 0x04
HEADER_SIZE = 8
BUFFER_SIZE = 64  # HID report size including the report ID
MAX_PAYLOAD = BUFFER_SIZE - HEADER_SIZE

CMD_TABLE_READ = 0x05
CMD_TABLE_WRITE = 0x06
CMD_HAPTICS_PRESET_WRITE = 0x7D
CMD_DPI_TABLE_WRITE = 0x7F

# Offsets in the table addressed by CMD_TABLE_READ / CMD_TABLE_WRITE.
OFFSET_DPI_SLOT = 0x16
OFFSET_HAPTICS_PRESET = 0x17
OFFSET_HORIZONTAL_SCROLL = 0x26

DPI_SLOTS = 4
DPI_MIN, DPI_MAX, DPI_STEP = 200, 6000, 100

HAPTICS_PRESETS = 4
HAPTICS_PRESET_SIZE = 7
TICK_MODES = {"round": 2, "sharp": 1}


class ProtocolError(Exception):
    pass


def build(cmd, size, offset=0, payload=b""):
    """Return a request, not yet padded to BUFFER_SIZE.

    size is the payload length for a write and the number of bytes wanted for
    a read. The checksum is the sum of all bytes after the checksum field.
    """
    if len(payload) > MAX_PAYLOAD or not 0 <= size <= 0xFF:
        raise ProtocolError("payload too large for one packet")
    body = bytes([cmd, size, offset & 0xFF, (offset >> 8) & 0xFF, (offset >> 16) & 0xFF]) + bytes(payload)
    checksum = sum(body) & 0xFFFF
    return bytes([REPORT_ID, checksum & 0xFF, checksum >> 8]) + body


def read_request(cmd, size, offset=0):
    return build(cmd, size, offset)


def write_request(cmd, payload, offset=0):
    return build(cmd, len(payload), offset, payload)


def pad(packet):
    return packet + bytes(BUFFER_SIZE - len(packet))


def parse_reply(request, reply):
    """Check that reply answers request and return its payload.

    Command, size and offset must echo the request, as the vendor software
    requires. The mouse also sends a checksum, which the vendor software
    ignores and we verify.
    """
    if len(reply) < HEADER_SIZE or len(reply) < HEADER_SIZE + reply[4]:
        raise ProtocolError(f"reply too short: {reply.hex(' ')}")
    end = HEADER_SIZE + reply[4]
    if reply[0] != REPORT_ID or reply[1] | reply[2] << 8 != sum(reply[3:end]) & 0xFFFF:
        raise ProtocolError(f"reply has a bad checksum: {reply[:end].hex(' ')}")
    if reply[3:8] != request[3:8]:
        raise ProtocolError(f"reply does not match request: {reply[:8].hex(' ')}")
    return bytes(reply[HEADER_SIZE : HEADER_SIZE + reply[4]])


def encode_dpi(dpi):
    if not DPI_MIN <= dpi <= DPI_MAX or dpi % DPI_STEP:
        raise ValueError(f"DPI must be {DPI_MIN}..{DPI_MAX} in steps of {DPI_STEP}")
    return (dpi - 1) // 100


def dpi_table(dpis):
    if len(dpis) != DPI_SLOTS:
        raise ValueError(f"expected {DPI_SLOTS} DPI values")
    return bytes(encode_dpi(d) for d in dpis) + bytes(8 - DPI_SLOTS)


def haptics_preset(mode, distance, force, length, speed_compensation, free_wheeling, threshold):
    checks = [
        ("tick distance", distance, 1, 36),
        ("tick force", force, 0, 100),
        ("tick length", length, 1, 50),
        ("speed compensation", speed_compensation, -10, 10),
        ("free-wheeling threshold", threshold, 1, 10),
    ]
    for name, value, low, high in checks:
        if not low <= value <= high:
            raise ValueError(f"{name} must be {low}..{high}")
    return bytes(
        [TICK_MODES[mode], distance, force, length, speed_compensation & 0xFF, int(bool(free_wheeling)), threshold]
    )
