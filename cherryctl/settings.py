"""Mouse settings kept on this computer.

The mouse only reports its selected DPI slot and haptics preset; DPI values,
the scroll setting and the presets' parameters cannot be read back. Like the
vendor software, we store them here and write them to the mouse.
"""
import copy
import json
import os

from . import protocol

DEFAULTS = {
    "dpis": [1000, 2000, 3000, 4000],
    "dpi_slot": 0,
    "horizontal_scroll": True,
    "haptics_preset": 0,
    "haptics": [
        {"name": "Basic", "mode": "round", "distance": 17, "force": 40, "length": 14,
         "speed_compensation": -3, "free_wheeling": False, "threshold": 6},
        {"name": "Smooth", "mode": "sharp", "distance": 10, "force": 24, "length": 13,
         "speed_compensation": 0, "free_wheeling": True, "threshold": 6},
        {"name": "Precision", "mode": "round", "distance": 7, "force": 40, "length": 14,
         "speed_compensation": 3, "free_wheeling": False, "threshold": 6},
        {"name": "Control", "mode": "sharp", "distance": 13, "force": 40, "length": 20,
         "speed_compensation": 0, "free_wheeling": False, "threshold": 6},
    ],
}


def path():
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, "cherryctl", "stream-ultimate-mouse.json")


def defaults():
    return copy.deepcopy(DEFAULTS)


def load():
    settings = defaults()
    try:
        with open(path()) as f:
            stored = json.load(f)
        validate({**settings, **stored})
        settings.update(stored)
    except (OSError, ValueError, KeyError, TypeError):
        pass  # missing or unusable file: start from the defaults
    return settings


def save(settings):
    os.makedirs(os.path.dirname(path()), exist_ok=True)
    tmp = path() + ".tmp"
    with open(tmp, "w") as f:
        json.dump(settings, f, indent=2)
    os.replace(tmp, path())


def preset_record(preset):
    return protocol.haptics_preset(
        preset["mode"], preset["distance"], preset["force"], preset["length"],
        preset["speed_compensation"], preset["free_wheeling"], preset["threshold"],
    )


def validate(settings):
    """Raise ValueError (or KeyError/TypeError) if settings cannot be sent."""
    protocol.dpi_table(settings["dpis"])
    if len(settings["haptics"]) != protocol.HAPTICS_PRESETS:
        raise ValueError("wrong number of haptics presets")
    for preset in settings["haptics"]:
        preset_record(preset)
    if not 0 <= settings["dpi_slot"] < protocol.DPI_SLOTS:
        raise ValueError("DPI slot out of range")
    if not 0 <= settings["haptics_preset"] < protocol.HAPTICS_PRESETS:
        raise ValueError("haptics preset out of range")


def apply(mouse, settings):
    """Write all settings to the mouse, in the order the vendor software uses."""
    validate(settings)
    mouse.write(protocol.CMD_DPI_TABLE_WRITE, protocol.dpi_table(settings["dpis"]))
    mouse.write(protocol.CMD_TABLE_WRITE, bytes([settings["dpi_slot"]]), protocol.OFFSET_DPI_SLOT)
    mouse.write(protocol.CMD_TABLE_WRITE, bytes([settings["horizontal_scroll"]]), protocol.OFFSET_HORIZONTAL_SCROLL)
    for index, preset in enumerate(settings["haptics"]):
        mouse.write(protocol.CMD_HAPTICS_PRESET_WRITE, preset_record(preset), index * protocol.HAPTICS_PRESET_SIZE)
    mouse.write(protocol.CMD_TABLE_WRITE, bytes([settings["haptics_preset"]]), protocol.OFFSET_HAPTICS_PRESET)


def read_selection(mouse, settings):
    """Update the selected DPI slot and haptics preset from the mouse."""
    slot = mouse.read_table(protocol.OFFSET_DPI_SLOT)[0]
    preset = mouse.read_table(protocol.OFFSET_HAPTICS_PRESET)[0]
    if slot < protocol.DPI_SLOTS:
        settings["dpi_slot"] = slot
    if preset < protocol.HAPTICS_PRESETS:
        settings["haptics_preset"] = preset
