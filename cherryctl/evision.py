"""Settings of CHERRY keyboards and mice that use the Evision protocol.

From static analysis of the vendor software only; see docs/evision-devices.md.
None of it has been tried on a device.
"""
import contextlib

from . import protocol

PROFILE_BLOCK = 0x40

# Command numbers that differ between the two command sets.
COMMANDS = {
    "Evision": {"stx": 0x01, "etx": 0x02, "colours_write": 0x0B, "battery": 0x1A},
    "Cherry": {"stx": 0x81, "etx": 0x82, "colours_write": 0x8B, "battery": 0x9A},
}

EFFECT_TABLES = {
    "Regular": {
        "Wave": 0x00, "Spectrum": 0x01, "Breathing": 0x02, "Static": 0x03, "Radar": 0x04, "Vortex": 0x05,
        "Fire": 0x06, "Stars": 0x07, "Custom": 0x08, "SineWave": 0x09, "Rolling": 0x0A, "Rain": 0x0B,
        "Curve": 0x0C, "RedHotMetal": 0x0D, "WaveMid": 0x0E, "Scan": 0x0F, "Radiation": 0x12,
        "Ripples": 0x13, "SingleKey": 0x15, "XAGA": 0x16, "Lightning": 0x17, "Flame": 0x18,
    },
    "RegularCherry": {
        "Radiation": 0x00, "Ripples": 0x01, "SingleKey": 0x02, "Static": 0x03, "Custom": 0x04,
        "Rainbow": 0x05, "Wave": 0x06, "Spectrum": 0x07, "Breathing": 0x08, "Rolling": 0x09,
        "Curve": 0x0A, "Scan": 0x0B,
    },
    "Reduced": {"Spectrum": 0x00, "Breathing": 0x01, "Static": 0x02},
    "ExtendedCherry": {
        "FlowingLight": 0x00, "Spectrum": 0x01, "Breathing": 0x02, "Static": 0x03, "Custom": 0x08,
        "Neon": 0x0A, "Flow": 0x0C, "Radiant": 0x12, "WaterRipple": 0x13, "Shadow": 0x15,
        "StarDots": 0x20, "Layers": 0x21, "SineWave": 0x22, "ColorSpring": 0x23, "SilentSnow": 0x24,
        "Loop": 0x25, "ColorGrid": 0x26, "Snowfall": 0x27, "Meteor": 0x28,
    },
}

DIRECTIONS = {
    "right": 0, "left": 1, "down": 2, "up": 3, "clockwise": 6, "counterclockwise": 7, "inward": 8, "outward": 9,
}

COLOUR_ENTRIES = 126

LOCKS = {"Win": 0x01, "AltTab": 0x02, "AltF4": 0x04, "FnAltF4": 0x08, "CtrlEsc": 0x10,
         "CtrlAltDel": 0x20, "Menu": 0x40, "AltEsc": 0x80}


def encode_dpi(formula, dpi):
    if formula == "Evision_V1":
        return dpi // 50 - 1 if dpi < 5000 else dpi // 100 + 0x31
    if formula == "Evision_V2":
        return dpi // 100 - 2 if dpi < 5000 else dpi // 200 + 0x17
    if formula == "Xtrfy":
        return dpi // 100
    if formula == "Cherry":
        return (dpi - 1) // 100
    raise ValueError(f"unknown DPI formula {formula}")


def in_range(name, value, bounds):
    low, high = bounds
    if not low <= value <= high:
        raise ValueError(f"{name} must be {low}..{high}")
    return value


class Device:
    """One connected device: its table entry plus a link to send packets."""

    def __init__(self, info, link):
        self.info = info
        self.link = link
        self.commands = COMMANDS[info["command_set"]]
        self.features = info["features"]
        self.payload_max = info["buffer_size"] - protocol.HEADER_SIZE

    def close(self):
        self.link.close()

    def need(self, feature):
        if feature not in self.features:
            raise ValueError(f"{self.info['name']} has no {feature.replace('_', ' ')} setting")
        return self.features[feature]

    # Packets

    def _request(self, cmd, size, offset=0, payload=b""):
        if self.info["checksum"]:
            return protocol.build(cmd, size, offset, payload)
        body = bytes([cmd, size, offset & 0xFF, (offset >> 8) & 0xFF, 0x55]) + bytes(payload)
        return bytes([protocol.REPORT_ID, 0, 0]) + body

    def _transfer(self, request):
        session_command = request[3] in (self.commands["stx"], self.commands["etx"])
        return self.link.transfer(
            request, size=self.info["buffer_size"], verify_checksum=self.info["checksum"],
            match_offset_high=not session_command,
        )

    def read(self, cmd, size, offset=0):
        data = b""
        while len(data) < size:
            chunk = min(self.payload_max, size - len(data))
            data += self._transfer(self._request(cmd, chunk, offset + len(data)))
        return data

    def write(self, cmd, payload, offset=0):
        for start in range(0, len(payload), self.payload_max):
            chunk = payload[start : start + self.payload_max]
            self._transfer(self._request(cmd, len(chunk), offset + start, chunk))

    @contextlib.contextmanager
    def session(self):
        """Wrap writes the way the vendor software does for lighting."""
        self._transfer(self._request(self.commands["stx"], 0))
        try:
            yield
        finally:
            self._transfer(self._request(self.commands["etx"], 0))

    # Profiles

    def profile(self):
        """The active on-board profile, from 0; 0 on devices without profiles."""
        if "profiles" not in self.features:
            return 0
        return self.read(protocol.CMD_TABLE_READ, 1, 0)[0]

    def set_profile(self, index):
        count = self.need("profiles")["count"]
        in_range("profile", index, (0, count - 1))
        self.write(protocol.CMD_TABLE_WRITE, bytes([index]), 0)

    def _base(self):
        return self.profile() * PROFILE_BLOCK

    # Lighting

    def lighting(self):
        """Read effect, brightness, delay and direction; colour is not readable."""
        config = self.need("lighting")
        table = EFFECT_TABLES[config["table"]]
        base = self._base()
        header = self.read(protocol.CMD_TABLE_READ, 8, base + 1)
        state = {
            "effect": next((name for name, value in table.items() if value == header[0] & ~0x40), None),
            "brightness": header[1],
            "delay": header[2],
            "direction": next((name for name, value in DIRECTIONS.items() if value == header[3]), None),
        }
        if "off_flag_offset" in config:
            state["on"] = self.read(protocol.CMD_TABLE_READ, 1, base + config["off_flag_offset"])[0] == 0
        return state

    def lighting_header(self, effect, brightness, delay, direction="right", random=False, colour=(255, 255, 255)):
        config = self.need("lighting")
        if effect not in config["effects"]:
            raise ValueError(f"effect must be one of: {', '.join(sorted(config['effects']))}")
        if direction not in DIRECTIONS:
            raise ValueError(f"direction must be one of: {', '.join(DIRECTIONS)}")
        return bytes([
            EFFECT_TABLES[config["table"]][effect],
            in_range("brightness", brightness, config["brightness"]),
            in_range("delay", delay, config["delay"]),
            DIRECTIONS[direction],
            int(bool(random)),
            *colour,
        ])

    def set_lighting(self, **values):
        header = self.lighting_header(**values)
        base = self._base()
        with self.session():
            self.write(protocol.CMD_TABLE_WRITE, header, base + 1)

    def set_lighting_on(self, on):
        config = self.need("lighting")
        if "off_flag_offset" not in config:
            raise ValueError(f"{self.info['name']} cannot switch its lighting off")
        base = self._base()
        with self.session():
            self.write(protocol.CMD_TABLE_WRITE, bytes([not on]), base + config["off_flag_offset"])

    def set_key_colours(self, colours):
        """colours maps key index to (r, g, b); other keys become black.

        The effect must be Custom for the colours to show.
        """
        self.need("lighting")
        table = bytearray(COLOUR_ENTRIES * 3)
        for index, colour in colours.items():
            in_range("key index", index, (0, COLOUR_ENTRIES - 1))
            table[index * 3 : index * 3 + 3] = bytes(colour)
        stride = self.features.get("profiles", {}).get("colours_stride", 0)
        offset = self.profile() * stride
        with self.session():
            self.write(self.commands["colours_write"], bytes(table), offset)

    # Keyboard performance

    def set_polling_rate(self, rate, dongle=False):
        if "mouse_performance" in self.features:
            raise ValueError("use the mouse settings to change this device's polling rate")
        config = self.need("keyboard_performance")
        rates = config["rates_dongle" if dongle else "rates_wired"]
        if rate not in rates:
            raise ValueError(f"polling rate must be one of: {', '.join(map(str, rates))}")
        offset = self._base() + (0x36 if dongle else 0x35)
        self.write(protocol.CMD_TABLE_WRITE, bytes([rates.index(rate)]), offset)

    def key_locks(self):
        available = self.need("keyboard_performance")["locks"]
        mask = self.read(protocol.CMD_TABLE_READ, 1, self._base() + 0x16)[0]
        if not mask & 1:
            return []
        return [name for name in available if mask & LOCKS[name]]

    def set_key_locks(self, names):
        available = self.need("keyboard_performance")["locks"]
        for name in names:
            if name not in available:
                raise ValueError(f"lock must be one of: {', '.join(available)}")
        mask = 0
        for name in names:
            mask |= LOCKS[name]
        # Bit 0 (Win) is also the master switch: without it nothing is locked.
        if mask and not mask & 1:
            raise ValueError("the other locks only work together with Win")
        base = self._base()
        with self.session():
            self.write(protocol.CMD_TABLE_WRITE, bytes([mask]), base + 0x16)

    # MC 2.1 / MC 3.1 mice

    def mouse_record(self, rate, dpis, slot):
        config = self.need("mouse_performance")
        low, high, step = config["dpi"]
        if len(dpis) != config["slots"]:
            raise ValueError(f"expected {config['slots']} DPI values")
        if rate not in config["rates"]:
            raise ValueError(f"polling rate must be one of: {', '.join(map(str, config['rates']))}")
        in_range("DPI slot", slot, (0, config["slots"] - 1))
        record = bytearray(10)
        record[0] = config["rates"].index(rate)
        for index, dpi in enumerate(dpis):
            if not low <= dpi <= high or dpi % step:
                raise ValueError(f"DPI must be {low}..{high} in steps of {step}")
            record[1 + 2 * index] = encode_dpi(config["formula"], dpi)
        record[9] = slot
        return bytes(record)

    def set_mouse(self, rate, dpis, slot):
        self.write(protocol.CMD_TABLE_WRITE, self.mouse_record(rate, dpis, slot), 0x0E)

    def mouse_slot(self):
        self.need("mouse_performance")
        return self.read(protocol.CMD_TABLE_READ, 10, 0x0E)[9]

    # Battery

    def battery(self):
        """Return (level in percent, charging)."""
        self.need("battery")
        level, charging = self.read(self.commands["battery"], 3)[:2]
        return level, bool(charging)
