# ==================================================
# Black Feather Foundry
#
# File:
# ui/components/foundry_tabs.py
#
# Purpose:
# Generic segmented tab/toggle control.
#
# Covers page-level tabs ("ABILITIES | THRESHOLDS |
# ..."), sub-tabs ("POSITIONING | PHASE TIMELINE"), and
# view toggles ("By Role | By Encounter") -- one row of
# mutually-exclusive compact buttons, reusing
# FoundryButton rather than a second button system.
#
# ==================================================

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QButtonGroup, QHBoxLayout, QWidget

from ui.components.foundry_button import ButtonRole, FoundryButton


class FoundryTabs(QWidget):
    """
    A row of mutually-exclusive compact tabs.

        tabs = FoundryTabs(["Abilities", "Thresholds", "Strategy"])
        tabs.tabChanged.connect(on_tab_changed)  # emits the selected text
    """

    tabChanged = Signal(str)

    def __init__(
        self,
        items: list[str],
        selected: str | None = None,
        parent=None,
    ):
        super().__init__(parent)

        layout = QHBoxLayout(self)

        layout.setContentsMargins(0, 0, 0, 0)

        layout.setSpacing(6)

        self._group = QButtonGroup(self)

        self._group.setExclusive(True)

        self._buttons: dict[str, FoundryButton] = {}

        for item in items:

            button = FoundryButton(
                item,
                role=ButtonRole.GHOST,
                compact=True,
            )

            button.setCheckable(True)

            button.clicked.connect(
                lambda _checked, name=item: self._select(name)
            )

            self._group.addButton(button)

            self._buttons[item] = button

            layout.addWidget(button)

        layout.addStretch()

        initial = selected or (items[0] if items else None)

        if initial:
            self.set_selected(initial)

    # --------------------------------------------------
    # Public API
    # --------------------------------------------------

    def set_selected(
        self,
        item: str,
    ):

        button = self._buttons.get(item)

        if button is not None:
            button.setChecked(True)

    def selected(self) -> str | None:

        for name, button in self._buttons.items():

            if button.isChecked():
                return name

        return None

    # --------------------------------------------------
    # Internal
    # --------------------------------------------------

    def _select(self, name: str):

        self.tabChanged.emit(name)
