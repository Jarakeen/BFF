# ==================================================
# Black Feather Foundry
#
# File:
# ui/components/foundry_status_badge.py
#
# Purpose:
# Generic colored status pill/dot.
#
# Data-driven: caller supplies a label and either a
# scale + key (looked up in Colors.SEVERITY / Colors.ROLE
# / Colors.STATUS) or an explicit color. No ESO-specific
# vocabulary lives here.
#
# ==================================================

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel

from ui.theme.colors import Colors
from ui.theme.fonts import Fonts

_SCALES = {
    "severity": Colors.SEVERITY,
    "role": Colors.ROLE,
    "status": Colors.STATUS,
}


def resolve_color(
    scale: str | None,
    key: str | None,
    color: str | None,
) -> str:
    """
    Resolve a badge color: an explicit color wins, then a
    (scale, key) lookup, then a neutral fallback.
    """

    if color:
        return color

    if scale and key:

        palette = _SCALES.get(scale, {})

        return palette.get(
            key,
            Colors.TEXT_MUTED,
        )

    return Colors.TEXT_MUTED


class FoundryStatusBadge(QLabel):
    """
    A small colored pill: [ ● Ready ] or [ Main Tank ].

        FoundryStatusBadge("Healer", scale="role", key="healer")
        FoundryStatusBadge("Extreme", scale="severity", key="extreme")
        FoundryStatusBadge("Pending", scale="status", key="pending")
        FoundryStatusBadge("Custom", color="#8B6FC9")
    """

    def __init__(
        self,
        text: str,
        *,
        scale: str | None = None,
        key: str | None = None,
        color: str | None = None,
        dot_only: bool = False,
        parent=None,
    ):
        super().__init__(parent)

        self.setProperty(
            "foundryStatusBadge",
            True,
        )

        self.setFont(
            Fonts.table()
        )

        self.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self._dot_only = dot_only

        self.set_value(
            text,
            scale=scale,
            key=key,
            color=color,
        )

    # --------------------------------------------------
    # Public API
    # --------------------------------------------------

    def set_value(
        self,
        text: str,
        *,
        scale: str | None = None,
        key: str | None = None,
        color: str | None = None,
    ):

        resolved = resolve_color(scale, key, color)

        self.setText(
            "●" if self._dot_only else text
        )

        if not self._dot_only:
            self.setToolTip(text)

        self.setStyleSheet(
            f"""
            background-color: {resolved}22;
            color: {resolved};
            border: 1px solid {resolved}55;
            """
        )
