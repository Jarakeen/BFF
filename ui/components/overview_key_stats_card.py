from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QLabel

from minmax.base_character_state import BaseCharacterState, CalculationTrace
from minmax.build_calculation_context import BuildCalculationContext
from minmax.core_stat_calculator import CoreStatState
from minmax.derived_stats import DerivedStatTrace
from minmax.stat_ids import StatId
from ui.components.foundry_card import FoundryCard


class OverviewKeyStatsCard(FoundryCard):
    """ESO-style character-sheet values with auditable calculation traces."""

    ROWS = (
        ("max_health", "Max Health", StatId.MAX_HEALTH, "base"),
        ("max_magicka", "Max Magicka", StatId.MAX_MAGICKA, "base"),
        ("max_stamina", "Max Stamina", StatId.MAX_STAMINA, "base"),
        ("health_recovery", "Health Recovery", StatId.HEALTH_RECOVERY, "base"),
        ("magicka_recovery", "Magicka Recovery", StatId.MAGICKA_RECOVERY, "base"),
        ("stamina_recovery", "Stamina Recovery", StatId.STAMINA_RECOVERY, "base"),
        ("spell_damage", "Spell Damage", StatId.SPELL_DAMAGE, "derived"),
        ("weapon_damage", "Weapon Damage", StatId.WEAPON_DAMAGE, "derived"),
        ("spell_critical", "Spell Critical", StatId.SPELL_CRITICAL, "derived"),
        ("weapon_critical", "Weapon Critical", StatId.WEAPON_CRITICAL, "derived"),
        ("spell_critical_damage", "Spell Critical Damage", StatId.CRITICAL_DAMAGE, "derived"),
        ("weapon_critical_damage", "Weapon Critical Damage", StatId.CRITICAL_DAMAGE, "derived"),
        ("spell_resistance", "Spell Resistance", StatId.SPELL_RESISTANCE, "derived"),
        ("physical_resistance", "Physical Resistance", StatId.PHYSICAL_RESISTANCE, "derived"),
        ("critical_resistance", "Critical Resistance", StatId.CRITICAL_RESISTANCE, "derived"),
        ("spell_penetration", "Spell Penetration", StatId.SPELL_PENETRATION, "derived"),
        ("physical_penetration", "Physical Penetration", StatId.PHYSICAL_PENETRATION, "derived"),
    )

    RATIO_STATS = {
        StatId.WEAPON_CRITICAL,
        StatId.SPELL_CRITICAL,
        StatId.CRITICAL_CHANCE,
        StatId.CRITICAL_DAMAGE,
        StatId.HEALING_DONE,
        StatId.HEALING_TAKEN,
    }

    def __init__(self, parent=None):
        super().__init__("Key Stats", "∑", parent)
        self.set_badge("CALCULATED")
        self._values: dict[str, QLabel] = {}
        self._states: dict[str, QLabel] = {}
        self._build()

    def _build(self) -> None:
        grid = QGridLayout()
        grid.setContentsMargins(6, 2, 6, 2)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(3)

        for row, (key, label_text, _stat, _layer) in enumerate(self.ROWS):
            name = QLabel(label_text)
            value = QLabel("—")
            value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            value.setProperty("overviewStatValue", True)
            source = QLabel("—")
            source.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            source.setProperty("overviewStatSource", True)
            grid.addWidget(name, row, 0)
            grid.addWidget(value, row, 1)
            grid.addWidget(source, row, 2)
            self._values[key] = value
            self._states[key] = source

        self.addLayout(grid)

        note = QLabel(
            "Calculated by Foundry. Hover a value to see the calculation trace; "
            "these are calculator results, not imported character-sheet values."
        )
        note.setWordWrap(True)
        note.setProperty("overviewNote", True)
        self.addWidget(note)

    @classmethod
    def _format(cls, stat: StatId, value: int | float | None) -> str:
        if value is None:
            return "—"
        if stat in cls.RATIO_STATS:
            return f"{float(value) * 100:.1f}%"
        return f"{int(round(value)):,}"

    @classmethod
    def _format_trace_value(cls, stat: StatId, value: float) -> str:
        if stat in cls.RATIO_STATS:
            return f"{value * 100:.2f}%"
        return f"{value:,.4f}".rstrip("0").rstrip(".")

    @classmethod
    def _base_tooltip(cls, trace: CalculationTrace) -> str:
        lines = [trace.stat.value.replace("_", " ").title()]
        for step in trace.steps:
            lines.append(
                f"{step.label}: {step.operation} {cls._format_trace_value(trace.stat, float(step.value))} "
                f"→ {cls._format_trace_value(trace.stat, float(step.result))}"
            )
        return "\n".join(lines)

    @classmethod
    def _derived_tooltip(cls, trace: DerivedStatTrace) -> str:
        lines = [trace.stat.value.replace("_", " ").title()]
        for label, operation, value, result in trace.steps:
            lines.append(
                f"{label}: {operation} {cls._format_trace_value(trace.stat, float(value))} "
                f"→ {cls._format_trace_value(trace.stat, float(result))}"
            )
        return "\n".join(lines)

    def set_context(self, context: BuildCalculationContext) -> None:
        """Render the exact calculation snapshot used for the selected build."""
        self.set_base(context.character_state)
        if context.core_state is not None:
            self._apply_derived(context.core_state)

    def set_base(self, state: BaseCharacterState) -> None:
        values = {
            StatId.MAX_HEALTH: state.max_health,
            StatId.MAX_MAGICKA: state.max_magicka,
            StatId.MAX_STAMINA: state.max_stamina,
            StatId.HEALTH_RECOVERY: state.health_recovery,
            StatId.MAGICKA_RECOVERY: state.magicka_recovery,
            StatId.STAMINA_RECOVERY: state.stamina_recovery,
        }
        for key, _label, stat, layer in self.ROWS:
            if layer != "base":
                continue
            value = values[stat]
            label = self._values[key]
            label.setText(self._format(stat, value))
            trace = state.traces.get(stat)
            label.setToolTip(self._base_tooltip(trace) if trace else "")
            self._states[key].setText("2A base")

    def set_core(self, state: CoreStatState) -> None:
        self.set_base(state.base_character)
        self._apply_derived(state)

    def _apply_derived(self, state: CoreStatState) -> None:
        for key, _label, stat, layer in self.ROWS:
            if layer != "derived":
                continue
            trace = state.derived.get(stat)
            value_label = self._values[key]
            if trace is None:
                value_label.setText("—")
                value_label.setToolTip("")
                self._states[key].setText("pending")
                continue
            value_label.setText(self._format(stat, trace.final_value))
            value_label.setToolTip(self._derived_tooltip(trace))
            self._states[key].setText("2C core")
