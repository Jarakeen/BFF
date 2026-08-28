from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QLabel

from minmax.base_character_state import BaseCharacterState
from minmax.core_stat_calculator import CoreStatState
from minmax.stat_ids import StatId
from ui.components.foundry_card import FoundryCard


class OverviewKeyStatsCard(FoundryCard):
    """Compact key-stat panel that exposes calculator values and provenance."""

    ROWS = (
        (StatId.MAX_HEALTH, "Max Health", "base"),
        (StatId.MAX_MAGICKA, "Max Magicka", "base"),
        (StatId.MAX_STAMINA, "Max Stamina", "base"),
        (StatId.HEALTH_RECOVERY, "Health Recovery", "base"),
        (StatId.MAGICKA_RECOVERY, "Magicka Recovery", "base"),
        (StatId.STAMINA_RECOVERY, "Stamina Recovery", "base"),
        (StatId.PHYSICAL_RESISTANCE, "Physical Resistance", "derived"),
        (StatId.SPELL_RESISTANCE, "Spell Resistance", "derived"),
        (StatId.CRITICAL_RESISTANCE, "Critical Resistance", "derived"),
        (StatId.WEAPON_DAMAGE, "Weapon Damage", "derived"),
        (StatId.SPELL_DAMAGE, "Spell Damage", "derived"),
        (StatId.CRITICAL_CHANCE, "Critical Chance", "derived"),
        (StatId.CRITICAL_DAMAGE, "Critical Damage", "derived"),
        (StatId.PHYSICAL_PENETRATION, "Penetration", "derived"),
        (StatId.HEALING_DONE, "Healing Done", "derived"),
    )

    def __init__(self, parent=None):
        super().__init__("Key Stats", "∑", parent)
        self.set_badge("CALCULATED")
        self._values: dict[StatId, QLabel] = {}
        self._states: dict[StatId, QLabel] = {}
        self._build()

    def _build(self) -> None:
        grid = QGridLayout()
        grid.setContentsMargins(6, 2, 6, 2)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(3)

        for row, (stat, label_text, _) in enumerate(self.ROWS):
            name = QLabel(label_text)
            value = QLabel("—")
            value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            value.setProperty("overviewStatValue", True)
            provenance = QLabel("—")
            provenance.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            provenance.setProperty("overviewStatSource", True)
            grid.addWidget(name, row, 0)
            grid.addWidget(value, row, 1)
            grid.addWidget(provenance, row, 2)
            self._values[stat] = value
            self._states[stat] = provenance

        self.addLayout(grid)

        note = QLabel(
            "Calculated by Foundry. Values are intentionally exposed for comparison "
            "against ESO and other references; no imported game values are substituted."
        )
        note.setWordWrap(True)
        note.setProperty("overviewNote", True)
        self.addWidget(note)

    @staticmethod
    def _format(stat: StatId, value: int | float | None) -> str:
        if value is None:
            return "—"
        if stat in {
            StatId.CRITICAL_CHANCE,
            StatId.CRITICAL_DAMAGE,
            StatId.HEALING_DONE,
            StatId.HEALING_TAKEN,
        }:
            return f"{float(value):.1f}%"
        return f"{int(value):,}"

    def set_base(self, state: BaseCharacterState) -> None:
        values = {
            StatId.MAX_HEALTH: state.max_health,
            StatId.MAX_MAGICKA: state.max_magicka,
            StatId.MAX_STAMINA: state.max_stamina,
            StatId.HEALTH_RECOVERY: state.health_recovery,
            StatId.MAGICKA_RECOVERY: state.magicka_recovery,
            StatId.STAMINA_RECOVERY: state.stamina_recovery,
        }
        for stat, value in values.items():
            self._values[stat].setText(self._format(stat, value))
            self._states[stat].setText("2A base")

    def set_core(self, state: CoreStatState) -> None:
        self.set_base(state.base_character)
        for stat, value_label in self._values.items():
            if stat in {
                StatId.MAX_HEALTH,
                StatId.MAX_MAGICKA,
                StatId.MAX_STAMINA,
                StatId.HEALTH_RECOVERY,
                StatId.MAGICKA_RECOVERY,
                StatId.STAMINA_RECOVERY,
            }:
                continue
            trace = state.derived.get(stat)
            if trace is None:
                value_label.setText("—")
                self._states[stat].setText("pending")
                continue
            value_label.setText(self._format(stat, trace.final_value))
            self._states[stat].setText("calculated")
