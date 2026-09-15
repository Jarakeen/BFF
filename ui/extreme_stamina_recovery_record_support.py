from __future__ import annotations

"""Expose the proof-closed U50 Stamina Recovery record in Extreme Build Lab."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout

from services.extreme_stamina_recovery_record_service import ExtremeStaminaRecoveryRecordService
from ui.components.foundry_card import FoundryCard

_INSTALLED = False
_OBJECTIVE = ExtremeStaminaRecoveryRecordService.OBJECTIVE_KEY


def _label(text: str, *, metric: bool = False, subtle: bool = False) -> QLabel:
    label = QLabel(text)
    label.setWordWrap(True)
    if metric:
        label.setProperty("metricValue", True)
    if subtle:
        label.setProperty("pageSubtitle", True)
    return label


def _display_payload() -> dict[str, str]:
    record = ExtremeStaminaRecoveryRecordService.record()
    build = dict(record.winning_build or {})

    named_sets = tuple(build.get("named_sets") or ())
    gear = " • ".join(f"{name} {pieces}pc" for name, pieces in named_sets)

    armor_traits = dict(build.get("armor_traits") or {})
    armor = " • ".join(
        f"{count} {trait}" for trait, count in armor_traits.items() if int(count or 0) > 0
    )
    setup_parts = (
        str(build.get("race") or "").strip(),
        str(build.get("armor_weight") or "").strip(),
        armor,
        str(build.get("mundus") or "").strip(),
        str(build.get("weapon_type") or "").strip(),
        str(build.get("provisioning") or "").strip(),
    )
    setup = " • ".join(part for part in setup_parts if part)

    route = " + ".join(str(value) for value in tuple(build.get("class_lines") or ()))
    active_bar = dict(build.get("active_bar") or {})
    bar_parts = []
    for key, value in active_bar.items():
        if isinstance(value, int):
            bar_parts.append(f"{value} {key}")
        else:
            bar_parts.append(f"{key}: {value}")
    bar = " • ".join(bar_parts)

    display_value = build.get("eso_display_value")
    if display_value is None:
        display_value = record.raw_value
    value_text = "—" if display_value is None else f"{float(display_value):,.0f}"

    record_kind = str(build.get("record_kind") or "").replace("_", " ").strip().title()
    update = str(build.get("game_update") or "").strip()
    status = record.proof_status.value.upper()
    context = " • ".join(part for part in (status, update, record_kind) if part)

    external = " • ".join(record.external_conditions)
    prerequisite = record.runtime_prerequisites[0] if record.runtime_prerequisites else ""
    explanation = record.explanation[0] if record.explanation else ""

    return {
        "value": value_text,
        "context": context,
        "setup": setup,
        "gear": gear,
        "route": route,
        "bar": bar,
        "external": external,
        "prerequisite": prerequisite,
        "explanation": explanation,
    }


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.extreme_optimization_page import ExtremeOptimizationPage

    original_build_ui = ExtremeOptimizationPage._build_ui

    def build_ui_with_record(self) -> None:
        original_build_ui(self)
        payload = _display_payload()

        card = FoundryCard("Proven Stamina Recovery Record")
        card.setObjectName("extremeStaminaRecoveryRecordCard")

        value = _label(payload["value"], metric=True)
        value.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        card.addWidget(value)
        card.addWidget(_label(payload["context"], subtle=True))
        card.addWidget(_label(payload["setup"]))
        card.addWidget(_label(payload["gear"]))
        card.addWidget(_label(payload["route"]))
        card.addWidget(_label(payload["bar"]))
        if payload["external"]:
            card.addWidget(_label(payload["external"]))
        if payload["prerequisite"]:
            card.addWidget(_label(payload["prerequisite"], subtle=True))
        if payload["explanation"]:
            card.addWidget(_label(payload["explanation"], subtle=True))

        parent = self.summary_card.parentWidget()
        layout = parent.layout() if parent is not None else None
        if isinstance(layout, QVBoxLayout):
            index = layout.indexOf(self.summary_card)
            layout.insertWidget(index + 1, card)
        else:
            self.add_workspace(card)

        self.stamina_recovery_record_card = card

        def sync_record_visibility(*_args) -> None:
            card.setVisible(str(self.objective_combo.currentData() or "") == _OBJECTIVE)

        self.objective_combo.currentIndexChanged.connect(sync_record_visibility)
        sync_record_visibility()

    ExtremeOptimizationPage._build_ui = build_ui_with_record
    _INSTALLED = True


__all__ = ["install"]
