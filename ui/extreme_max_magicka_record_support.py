from __future__ import annotations

"""Expose the proof-closed Update 50 Max Magicka record in Extreme Build Lab."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout

from ui.components.foundry_card import FoundryCard

_OBJECTIVE = "max_magicka"
_RECORD_VALUE = 108_319
_NON_EMPEROR_REFERENCE = 69_262
_CONTEXT = "Update 50 • Active Emperor • 6 Home Keeps"
_GEAR = (
    "Crafty Alfiq 5pc • Grace of the Ancients 3pc • "
    "Armor of the Trainee 2pc • Infernal Guardian 1pc • Nightflame 1pc"
)
_SETUP = "High Elf • Sorcerer • 64 Magicka • The Mage • Crusty Sweetroll"
_ARMOR = "3 armor types • 4 Divines • 3 Infused • front/back tied"


_RECORD_CARD_ATTRIBUTES = (
    "max_health_record_card",
    "max_stamina_record_card",
    "health_recovery_record_card",
    "magicka_recovery_record_card",
    "stamina_recovery_record_card",
)


def _label(text: str, *, metric: bool = False, subtle: bool = False) -> QLabel:
    label = QLabel(text)
    label.setWordWrap(True)
    if metric:
        label.setProperty("metricValue", True)
    if subtle:
        label.setProperty("pageSubtitle", True)
    return label


def apply_extreme_max_magicka_record(page) -> None:
    """Attach the Max Magicka record card to one constructed Extreme page."""
    if getattr(page, "max_magicka_record_card", None) is not None:
        return

    card = FoundryCard("Proven Max Magicka Record")
    card.setObjectName("extremeMaxMagickaRecordCard")

    value = _label(f"{_RECORD_VALUE:,}", metric=True)
    value.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    card.addWidget(value)
    card.addWidget(_label(_CONTEXT, subtle=True))
    card.addWidget(_label(_SETUP))
    card.addWidget(_label(_GEAR))
    card.addWidget(_label(_ARMOR))
    card.addWidget(
        _label(
            f"Proof closed across all modeled axes. Same build without Emperor: {_NON_EMPEROR_REFERENCE:,} Max Magicka.",
            subtle=True,
        )
    )

    parent = page.summary_card.parentWidget()
    layout = parent.layout() if parent is not None else None
    if isinstance(layout, QVBoxLayout):
        # The legacy wrapper was installed first and therefore rendered last once
        # the full wrapper stack unwound. Preserve that visible ordering while
        # removing the runtime class replacement.
        insert_at = layout.indexOf(page.summary_card) + 1
        for attribute in _RECORD_CARD_ATTRIBUTES:
            existing = getattr(page, attribute, None)
            if existing is not None:
                index = layout.indexOf(existing)
                if index >= 0:
                    insert_at = max(insert_at, index + 1)
        layout.insertWidget(insert_at, card)
    else:
        page.add_workspace(card)

    page.max_magicka_record_card = card

    def sync_record_visibility(*_args) -> None:
        card.setVisible(str(page.objective_combo.currentData() or "") == _OBJECTIVE)

    page.objective_combo.currentIndexChanged.connect(sync_record_visibility)
    sync_record_visibility()


def install() -> None:
    """Compatibility no-op; presentation is composed on the page instance."""


__all__ = ["apply_extreme_max_magicka_record", "install"]
