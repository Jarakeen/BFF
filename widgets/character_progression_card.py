from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QGridLayout, QLabel, QSpinBox

from ui.components.foundry_card import FoundryCard


MAX_ATTRIBUTE_POINTS = 64


class CharacterProgressionCard(FoundryCard):
    """Compact editor for persistent character state needed by MinMax."""

    def __init__(self, parent=None):
        super().__init__("Character Progression", "✦", parent)
        self.vampire = QCheckBox("Vampire")
        self.werewolf = QCheckBox("Werewolf")
        self.health = self._spin()
        self.magicka = self._spin()
        self.stamina = self._spin()
        self.total = QLabel()
        self.total.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.total.setProperty("overviewStatValue", True)

        grid = QGridLayout()
        grid.setContentsMargins(6, 2, 6, 2)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(4)
        grid.addWidget(self.vampire, 0, 0)
        grid.addWidget(self.werewolf, 0, 1)
        grid.addWidget(QLabel("Health"), 1, 0)
        grid.addWidget(self.health, 1, 1)
        grid.addWidget(QLabel("Magicka"), 1, 2)
        grid.addWidget(self.magicka, 1, 3)
        grid.addWidget(QLabel("Stamina"), 1, 4)
        grid.addWidget(self.stamina, 1, 5)
        grid.addWidget(QLabel("Total / 64"), 1, 6)
        grid.addWidget(self.total, 1, 7)
        self.addLayout(grid)

        note = QLabel("64 total attribute points are available for the character's lifetime.")
        note.setProperty("overviewNote", True)
        self.addWidget(note)

        self.vampire.toggled.connect(self._sync_forms)
        self.werewolf.toggled.connect(self._sync_forms)
        for spin in (self.health, self.magicka, self.stamina):
            spin.valueChanged.connect(self._update_total)
        self._sync_forms()
        self._update_total()

    @staticmethod
    def _spin() -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(0, MAX_ATTRIBUTE_POINTS)
        spin.setFixedWidth(70)
        return spin

    def _sync_forms(self):
        if self.vampire.isChecked() and self.werewolf.isChecked():
            sender = self.sender()
            if sender is self.vampire:
                self.werewolf.blockSignals(True)
                self.werewolf.setChecked(False)
                self.werewolf.blockSignals(False)
            else:
                self.vampire.blockSignals(True)
                self.vampire.setChecked(False)
                self.vampire.blockSignals(False)

    def _update_total(self):
        values = (self.health.value(), self.magicka.value(), self.stamina.value())
        total = sum(values)
        self.total.setText(str(total))
        for spin, value in zip((self.health, self.magicka, self.stamina), values):
            spin.setMaximum(min(MAX_ATTRIBUTE_POINTS, MAX_ATTRIBUTE_POINTS - (total - value)))
        self.total.setProperty("attributeComplete", total == MAX_ATTRIBUTE_POINTS)
        self.total.style().unpolish(self.total)
        self.total.style().polish(self.total)

    def set_values(self, *, health: int = 0, magicka: int = 0, stamina: int = 0, vampire: bool = False, werewolf: bool = False):
        self.vampire.blockSignals(True)
        self.werewolf.blockSignals(True)
        self.health.blockSignals(True)
        self.magicka.blockSignals(True)
        self.stamina.blockSignals(True)
        self.vampire.setChecked(bool(vampire) and not bool(werewolf))
        self.werewolf.setChecked(bool(werewolf) and not bool(vampire))
        self.health.setValue(max(0, min(MAX_ATTRIBUTE_POINTS, int(health))) if health is not None else 0)
        self.magicka.setValue(max(0, min(MAX_ATTRIBUTE_POINTS, int(magicka))) if magicka is not None else 0)
        self.stamina.setValue(max(0, min(MAX_ATTRIBUTE_POINTS, int(stamina))) if stamina is not None else 0)
        self.stamina.blockSignals(False)
        self.magicka.blockSignals(False)
        self.health.blockSignals(False)
        self.werewolf.blockSignals(False)
        self.vampire.blockSignals(False)
        self._sync_forms()
        self._update_total()

    @property
    def values(self) -> dict[str, int | bool]:
        return {
            "health": self.health.value(),
            "magicka": self.magicka.value(),
            "stamina": self.stamina.value(),
            "vampire": self.vampire.isChecked(),
            "werewolf": self.werewolf.isChecked(),
        }
