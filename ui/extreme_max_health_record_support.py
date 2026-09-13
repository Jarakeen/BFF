from __future__ import annotations

"""Expose the proof-closed Update 50 Max Health record in Extreme Build Lab."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout

from ui.components.foundry_card import FoundryCard

_INSTALLED = False
_OBJECTIVE = "max_health"
_RECORD_VALUE = 147_307
_NON_EMPEROR_REFERENCE = 98_422
_CONTEXT = "Update 50 • Active Emperor • 6 Home Keeps"
_SETUP = (
    "Imperial • Bone Tyrant + Green Balance + Shadow • "
    "64 Health • The Lord • Crusty Bread"
)
_GEAR = (
    "Plague Doctor 5pc • Endurance 2pc • Scourge Harvester 1pc • "
    "Armor of the Trainee 1pc • Prophet's 1pc • Gaze of Sithis 1pc • "
    "Druid's Braid 1pc"
)
_ARMOR = "7 Heavy • 4 Divines • 3 Infused • equivalent +16% armor frontiers proven"
_RUNTIME = "Maturation • Minor Toughness • front/back denominator closed"


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

        card = FoundryCard("Proven Max Health Record")
        card.setObjectName("extremeMaxHealthRecordCard")

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
                f"Same winning build without Emperor: {_NON_EMPEROR_REFERENCE:,} Max Health. "
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

        self.max_health_record_card = card

        def sync_record_visibility(*_args) -> None:
            card.setVisible(str(self.objective_combo.currentData() or "") == _OBJECTIVE)

        self.objective_combo.currentIndexChanged.connect(sync_record_visibility)
        sync_record_visibility()

    ExtremeOptimizationPage._build_ui = build_ui_with_record
    _INSTALLED = True


__all__ = ["install"]
