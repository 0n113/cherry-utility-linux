"""Graphical settings window for the CHERRY Stream Ultimate Mouse.

    cherryctl gui          # the connected mouse
    cherryctl gui --demo   # a simulated mouse
    cherryctl gui --demo-device "MX board 3 0S"   # a simulated keyboard

Without a Stream Ultimate Mouse, the first other supported device found gets
an experimental window (gui_evision).
"""
import copy
import sys

from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QCheckBox, QComboBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
    QMainWindow, QPushButton, QRadioButton, QSlider, QSpinBox, QVBoxLayout, QWidget,
)
from PySide6.QtCore import Qt

from . import device, fake, protocol, settings

POLL_MS = 2000


class Worker(QObject):
    """Talks to the mouse off the GUI thread."""

    connected = Signal(dict)  # selection read from the mouse
    disconnected = Signal(str)  # reason shown to the user, may be empty
    applied = Signal()
    failed = Signal(str)

    def __init__(self, demo):
        super().__init__()
        self.demo = demo
        self.mouse = None

    def _open(self):
        if self.demo:
            return fake.FakeMouse()
        path = device.find()
        return device.Mouse(path) if path else None

    def _drop(self, reason=""):
        if self.mouse:
            try:
                self.mouse.close()
            except OSError:
                pass
        self.mouse = None
        self.disconnected.emit(reason)

    @Slot()
    def poll(self):
        """Connect to the mouse when it appears, notice when it goes away."""
        if self.mouse:
            if not self.demo and not device.find():
                self._drop()
            return
        try:
            self.mouse = self._open()
            if not self.mouse:
                return
            selection = {}
            settings.read_selection(self.mouse, selection)
            self.connected.emit(selection)
        except PermissionError:
            self.mouse = None
            self.disconnected.emit("No permission for the mouse. Install udev/70-cherry.rules, then replug the cable.")
        except (OSError, protocol.ProtocolError) as err:
            self._drop(str(err))

    @Slot(dict)
    def apply(self, values):
        if not self.mouse:
            self.failed.emit("The mouse is not connected.")
            return
        try:
            settings.apply(self.mouse, values)
            settings.save(values)
            self.applied.emit()
        except ValueError as err:
            self.failed.emit(str(err))
        except (OSError, protocol.ProtocolError) as err:
            self._drop(f"Writing failed: {err}")


class Slider(QWidget):
    """A slider with its value shown next to it."""

    changed = Signal()

    def __init__(self, low, high):
        super().__init__()
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(low, high)
        self.label = QLabel()
        self.label.setMinimumWidth(32)
        self.label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.slider)
        layout.addWidget(self.label)
        self.slider.valueChanged.connect(self._on_change)
        self._on_change(self.slider.value())

    def _on_change(self, value):
        self.label.setText(str(value))
        self.changed.emit()

    def value(self):
        return self.slider.value()

    def set_value(self, value):
        self.slider.setValue(value)


class Window(QMainWindow):
    apply_requested = Signal(dict)
    poll_requested = Signal()

    def __init__(self, demo=False):
        super().__init__()
        self.setWindowTitle("CHERRY Stream Ultimate Mouse" + (" (simulated)" if demo else ""))
        self.values = settings.load()
        self.loading = False

        self.status = QLabel()
        self.status.setWordWrap(True)

        body = QWidget()
        column = QVBoxLayout(body)
        column.addWidget(self.status)
        column.addWidget(self._dpi_box())
        column.addWidget(self._haptics_box())
        column.addLayout(self._buttons())
        self.setCentralWidget(body)

        self._show_values()
        self.set_connected(False, "")

        self.thread = QThread(self)
        self.worker = Worker(demo)
        self.worker.moveToThread(self.thread)
        self.worker.connected.connect(self.on_connected)
        self.worker.disconnected.connect(lambda reason: self.set_connected(False, reason))
        self.worker.applied.connect(self.on_applied)
        self.worker.failed.connect(self.on_failed)
        self.apply_requested.connect(self.worker.apply)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.worker.poll)
        self.poll_requested.connect(self.worker.poll)
        self.thread.start()
        self.timer.start(POLL_MS)
        self.poll_requested.emit()

    # Layout

    def _dpi_box(self):
        box = QGroupBox("Pointer")
        form = QFormLayout(box)
        self.slot_group = QButtonGroup(self)
        self.dpi_spins = []
        for index in range(protocol.DPI_SLOTS):
            radio = QRadioButton(f"Slot {index + 1}")
            self.slot_group.addButton(radio, index)
            spin = QSpinBox()
            spin.setRange(protocol.DPI_MIN, protocol.DPI_MAX)
            spin.setSingleStep(protocol.DPI_STEP)
            spin.setSuffix(" DPI")
            spin.valueChanged.connect(self._edited)
            spin.editingFinished.connect(lambda s=spin: s.setValue(s.value() - s.value() % protocol.DPI_STEP))
            self.dpi_spins.append(spin)
            form.addRow(radio, spin)
        self.slot_group.idClicked.connect(self._edited)
        self.hscroll = QCheckBox("Horizontal scrolling")
        self.hscroll.toggled.connect(self._edited)
        form.addRow(self.hscroll)
        return box

    def _haptics_box(self):
        box = QGroupBox("Scroll wheel haptics")
        form = QFormLayout(box)
        self.preset = QComboBox()
        self.preset.currentIndexChanged.connect(self._preset_selected)
        form.addRow("Preset", self.preset)
        self.mode = QComboBox()
        self.mode.addItem("Round", "round")
        self.mode.addItem("Sharp", "sharp")
        self.distance = Slider(1, 36)
        self.force = Slider(0, 100)
        self.length = Slider(1, 50)
        self.speed = Slider(-10, 10)
        self.free_wheeling = QCheckBox("Free-wheeling when scrolling fast")
        self.threshold = Slider(1, 10)
        form.addRow("Tick shape", self.mode)
        form.addRow("Tick distance", self.distance)
        form.addRow("Tick force", self.force)
        form.addRow("Tick length", self.length)
        form.addRow("Speed compensation", self.speed)
        form.addRow(self.free_wheeling)
        form.addRow("Free-wheeling threshold", self.threshold)
        self.mode.currentIndexChanged.connect(self._edited)
        for slider in (self.distance, self.force, self.length, self.speed, self.threshold):
            slider.changed.connect(self._edited)
        self.free_wheeling.toggled.connect(self._edited)
        return box

    def _buttons(self):
        row = QHBoxLayout()
        self.reset_button = QPushButton("Reset to defaults")
        self.reset_button.clicked.connect(self._reset)
        self.apply_button = QPushButton("Apply")
        self.apply_button.setDefault(True)
        self.apply_button.clicked.connect(self._apply)
        row.addWidget(self.reset_button)
        row.addStretch()
        row.addWidget(self.apply_button)
        return row

    # Values <-> widgets

    def _show_values(self):
        self.loading = True
        for spin, dpi in zip(self.dpi_spins, self.values["dpis"]):
            spin.setValue(dpi)
        self.slot_group.button(self.values["dpi_slot"]).setChecked(True)
        self.hscroll.setChecked(self.values["horizontal_scroll"])
        self.preset.clear()
        for preset in self.values["haptics"]:
            self.preset.addItem(preset["name"])
        self.preset.setCurrentIndex(self.values["haptics_preset"])
        self._show_preset()
        self.loading = False

    def _show_preset(self):
        was_loading, self.loading = self.loading, True
        preset = self.values["haptics"][self.values["haptics_preset"]]
        self.mode.setCurrentIndex(self.mode.findData(preset["mode"]))
        self.distance.set_value(preset["distance"])
        self.force.set_value(preset["force"])
        self.length.set_value(preset["length"])
        self.speed.set_value(preset["speed_compensation"])
        self.free_wheeling.setChecked(preset["free_wheeling"])
        self.threshold.set_value(preset["threshold"])
        self.loading = was_loading

    def _preset_selected(self, index):
        if self.loading or index < 0:
            return
        self.values["haptics_preset"] = index
        self._show_preset()
        self._mark_changed()

    def _edited(self, *_):
        if self.loading:
            return
        self.values["dpis"] = [spin.value() - spin.value() % protocol.DPI_STEP for spin in self.dpi_spins]
        self.values["dpi_slot"] = self.slot_group.checkedId()
        self.values["horizontal_scroll"] = self.hscroll.isChecked()
        preset = self.values["haptics"][self.values["haptics_preset"]]
        preset.update(
            mode=self.mode.currentData(), distance=self.distance.value(), force=self.force.value(),
            length=self.length.value(), speed_compensation=self.speed.value(),
            free_wheeling=self.free_wheeling.isChecked(), threshold=self.threshold.value(),
        )
        self._mark_changed()

    def _mark_changed(self):
        if self.is_connected:
            self.status.setText("Changes are not on the mouse yet. Press Apply to write them.")

    def _reset(self):
        self.values = settings.defaults()
        self._show_values()
        self._mark_changed()

    def _apply(self):
        self.apply_button.setEnabled(False)
        self.status.setText("Writing to the mouse…")
        self.apply_requested.emit(copy.deepcopy(self.values))

    # Worker results

    def set_connected(self, is_connected, reason):
        self.is_connected = is_connected
        self.apply_button.setEnabled(is_connected)
        if not is_connected:
            self.status.setText(
                reason or "Mouse not found. Connect it with the USB cable; it cannot be configured through the dongle."
            )

    def on_connected(self, selection):
        self.values.update(selection)
        self._show_values()
        self.set_connected(True, "")
        self.status.setText(
            "Mouse connected. DPI values and haptics presets cannot be read from the mouse; "
            "the values shown are the ones last applied from this computer."
        )

    def on_applied(self):
        self.apply_button.setEnabled(True)
        self.status.setText("Settings written to the mouse.")

    def on_failed(self, message):
        self.apply_button.setEnabled(self.is_connected)
        self.status.setText(f"Could not apply: {message}")

    def closeEvent(self, event):
        self.timer.stop()
        self.thread.quit()
        self.thread.wait()
        super().closeEvent(event)


def other_device(demo, demo_device):
    """An Evision device to show instead of the mouse, or None."""
    from . import evision, table

    if demo_device:
        info = next((d for d in table.load() if d["name"] == demo_device), None)
        if not info:
            sys.exit(f"unknown device {demo_device!r}; names are in cherryctl/data/devices.json")
        return evision.Device(info, fake.FakeLink(info["checksum"]))
    if demo or device.find():
        return None
    for path, info in device.scan(table.load()):
        try:
            return evision.Device(info, device.Link(path))
        except OSError:
            continue
    return None


def main(demo=False, demo_device=None):
    app = QApplication(sys.argv[:1])
    app.setApplicationName("cherryctl")
    app.setDesktopFileName("cherryctl")
    dev = other_device(demo, demo_device)
    if dev:
        from . import gui_evision

        window = gui_evision.Window(dev)
    else:
        window = Window(demo=demo)
    window.show()
    sys.exit(app.exec())
