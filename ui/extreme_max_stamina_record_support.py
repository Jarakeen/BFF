from __future__ import annotations

"""Expose the proof-closed Update 50 Max Stamina record in Extreme Build Lab."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout

from ui.components.foundry_card import FoundryCard

_INSTALLED = False
_OBJECTIVE = "max_stamina"
_RECORD_VALUE = 101_930
_NON_EMPEROR_REFERENCE = 64_085
_CONTEXT = "Update 50 • Active Emperor • 6 Home Keeps"
_SETUP = (
    "Bosmer • Sorcerer + Dark Magic + Siphoning • "
    "64 Stamina • The Tower • Hearty Garlic Corn Chowder"
)
_GEAR = (
    "Draugr Hulk 5pc • Darkstride 3pc • Agility 2pc • "
    "Spawn of Mephala 1pc • Swarm Mother 1pc"
)
_ARMOR = "3 armor types • 4 Divines • 3 Infused • front/back denominator closed"
_RUNTIME = "Dominant route: Daedric Summoning + Dark Magic + Siphoning"


def _label(text: str, *, metric: bool = False, subtle: bool = False) -> QLabel:
    label = QLabel(text)
    label.setWordWrap(True)
    if metric:
        label.setProperty("metricValue", True)
    if subtle:
        label.setProperty("pageSubtitle", True)
    return label


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.extreme_optimization_page import ExtremeOptimizationPage

    original_build_ui = ExtremeOptimizationPage._build_ui

    def build_ui_with_record(self) -> None:
        original_build_ui(self)

        card = FoundryCard("Proven Max Stamina Record")
        card.setObjectName("extremeMaxStaminaRecordCard")

        value = _label(f"{_RECORD_VALUE:,}", metric=True)
        value.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        card.addWidget(value)
        card.addWidget(_label(_CONTEXT, subtle=True))
        card.addWidget(_label(_SETUP))
        card.addWidget(_label(_GEAR))
        card.addWidget(_label(_ARMOR))
        card.addWidget(_label(_RUNTIME))
        card.addWidget(
            _label(
                "Proof closed across all modeled axes. "
                f"Same winning build without Emperor: {_NON_EMPEROR_REFERENCE:,} Max Stamina. "
                "That companion value is not claimed as a separately proven non-Emperor global optimum.",
                subtle=True,
            )
        )

        parent = self.summary_card.parentWidget()
        layout = parent.layout() if parent is not None else None
        if isinstance(layout, QVBoxLayout):
            index = layout.indexOf(self.summary_card)
            layout.insertWidget(index + 1, card)
        else:
            self.add_workspace(card)

        self.max_stamina_record_card = card

        def sync_record_visibility(*_args) -> None:
            card.setVisible(str(self.objective_combo.currentData() or "") == _OBJECTIVE)

        self.objective_combo.currentIndexChanged.connect(sync_record_visibility)
        sync_record_visibility()

    ExtremeOptimizationPage._build_ui = build_ui_with_record
    _INSTALLED = True


__all__ = ["install"]
