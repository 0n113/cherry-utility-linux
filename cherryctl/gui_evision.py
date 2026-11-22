"""Settings window for other CHERRY keyboards and mice (experimental).

Built from code analysis only; never run against such a device.
"""
from PySide6.QtCore import QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox, QColorDialog, QComboBox, QFormLayout, QGroupBox, QLabel, QMainWindow, QPushButton,
    QSpinBox, QVBoxLayout, QWidget,
)

from . import evision, protocol

BATTERY_MS = 3000


class Window(QMainWindow):
    def __init__(self, dev):
        super().__init__()
        self.dev = dev
        self.features = dev.features
        self.colour = QColor(255, 255, 255)
        self.setWindowTitle(f"CHERRY {dev.info['name']} (experimental)")

        self.status = QLabel(
            "Experimental: these settings come from code analysis and have not been tried on this model."
        )
        self.status.setWordWrap(True)
        body = QWidget()
        column = QVBoxLayout(body)
        column.addWidget(self.status)
        if "profiles" in self.features:
            column.addWidget(self._profile_box())
        if "lighting" in self.features:
            column.addWidget(self._lighting_box())
        if "keyboard_performance" in self.features:
            column.addWidget(self._performance_box())
        if "battery" in self.features:
            self.battery = QLabel("Battery: …")
            column.addWidget(self.battery)
            self.timer = QTimer(self)
            self.timer.timeout.connect(self._read_battery)
            self.timer.start(BATTERY_MS)
        column.addStretch()
        self.setCentralWidget(body)
        self._read_state()

    def _run(self, action, done="Written to the device."):
        """Run a device action and report the outcome in the status line."""
        try:
            result = action()
        except (ValueError, OSError, protocol.ProtocolError) as err:
            self.status.setText(f"Failed: {err}")
            return None
        if done:
            self.status.setText(done)
        return result

    # Profiles

    def _profile_box(self):
        box = QGroupBox("On-board profile")
        form = QFormLayout(box)
        self.profile = QComboBox()
        for index in range(self.features["profiles"]["count"]):
            self.profile.addItem(f"Profile {index + 1}")
        self.profile.activated.connect(self._set_profile)
        form.addRow("Active profile", self.profile)
        return box

    def _set_profile(self, index):
        self._run(lambda: self.dev.set_profile(index))
        self._read_state()

    # Lighting

    def _lighting_box(self):
        config = self.features["lighting"]
        box = QGroupBox("Lighting")
        form = QFormLayout(box)
        self.effect = QComboBox()
        self.effect.addItems(sorted(config["effects"]))
        self.brightness = QSpinBox()
        self.brightness.setRange(*config["brightness"])
        self.brightness.setValue(config["brightness"][1])
        self.speed = QSpinBox()
        self.speed.setRange(0, config["delay"][1] - config["delay"][0])
        self.direction = QComboBox()
        self.direction.addItems(list(evision.DIRECTIONS))
        self.random = QCheckBox("Random colours")
        self.colour_button = QPushButton()
        self.colour_button.clicked.connect(self._pick_colour)
        self._show_colour()
        form.addRow("Effect", self.effect)
        form.addRow("Brightness", self.brightness)
        form.addRow("Speed", self.speed)
        form.addRow("Direction", self.direction)
        form.addRow("Colour", self.colour_button)
        form.addRow(self.random)
        if "off_flag_offset" in config:
            self.lights_on = QCheckBox("Lighting on")
            self.lights_on.setChecked(True)
            self.lights_on.clicked.connect(lambda on: self._run(lambda: self.dev.set_lighting_on(on)))
            form.addRow(self.lights_on)
        apply_button = QPushButton("Apply lighting")
        apply_button.clicked.connect(self._apply_lighting)
        form.addRow(apply_button)
        form.addRow(QLabel("Not every effect uses every setting."))
        form.addRow(QLabel("The colour cannot be read back."))
        return box

    def _show_colour(self):
        self.colour_button.setText(self.colour.name())
        self.colour_button.setStyleSheet(f"background-color: {self.colour.name()}")

    def _pick_colour(self):
        colour = QColorDialog.getColor(self.colour, self)
        if colour.isValid():
            self.colour = colour
            self._show_colour()

    def _apply_lighting(self):
        delay_low, delay_high = self.features["lighting"]["delay"]
        self._run(lambda: self.dev.set_lighting(
            effect=self.effect.currentText(), brightness=self.brightness.value(),
            delay=delay_high - self.speed.value(), direction=self.direction.currentText(),
            random=self.random.isChecked(),
            colour=(self.colour.red(), self.colour.green(), self.colour.blue()),
        ))

    # Performance

    def _performance_box(self):
        config = self.features["keyboard_performance"]
        box = QGroupBox("Performance")
        form = QFormLayout(box)
        for label, key, dongle in (("Polling rate (cable)", "rates_wired", False),
                                   ("Polling rate (dongle)", "rates_dongle", True)):
            if not config[key]:
                continue
            combo = QComboBox()
            combo.addItem("Leave unchanged", None)
            for rate in config[key]:
                combo.addItem(f"{rate} Hz", rate)
            combo.activated.connect(lambda _, c=combo, d=dongle: self._set_rate(c.currentData(), d))
            form.addRow(label, combo)
        form.addRow(QLabel("The rate cannot be read back."))
        return box

    def _set_rate(self, rate, dongle):
        if rate is not None:
            self._run(lambda: self.dev.set_polling_rate(rate, dongle=dongle))

    # Reading

    def _read_state(self):
        if "profiles" in self.features:
            index = self._run(self.dev.profile, done="")
            if index is not None and index < self.profile.count():
                self.profile.setCurrentIndex(index)
        if "lighting" in self.features:
            state = self._run(self.dev.lighting, done="")
            if state:
                delay_high = self.features["lighting"]["delay"][1]
                if state["effect"]:
                    self.effect.setCurrentText(state["effect"])
                self.brightness.setValue(state["brightness"])
                self.speed.setValue(delay_high - state["delay"])
                if state["direction"]:
                    self.direction.setCurrentText(state["direction"])
                if "on" in state:
                    self.lights_on.setChecked(state["on"])
        if "battery" in self.features:
            self._read_battery()

    def _read_battery(self):
        try:
            level, charging = self.dev.battery()
        except (ValueError, OSError, protocol.ProtocolError):
            # Each failed read blocks the window for the reply timeout, so
            # do not keep asking a device that does not answer.
            self.timer.stop()
            self.battery.setText("Battery: unknown")
            return
        self.battery.setText(f"Battery: {level} %{', charging' if charging else ''}")

    def closeEvent(self, event):
        self.dev.close()
        super().closeEvent(event)
