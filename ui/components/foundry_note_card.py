# ==================================================
# Black Feather Foundry
#
# File:
# ui/components/foundry_note_card.py
#
# Purpose:
# The parchment/journal card motif (Quick Notes, Key
# Reminders, Historical Notes, Tonight's Directive).
#
# Deliberately distinct from FoundryCard -- a second
# "register," not a second design system: it reuses the
# same spacing/radius tokens and only swaps in the paper
# palette from colors.py. Plain-text by default; pass
# editable=True for the rich-text "My Notes" case.
#
# ==================================================

from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ui.components.foundry_icon import FoundryIcon
from ui.theme.colors import Colors
from ui.theme.fonts import Fonts
from ui.theme.metrics import Metrics


class FoundryNoteCard(QFrame):
    """
    A parchment-styled note panel.

        FoundryNoteCard("Key Reminders", body="Portals at 25%.")
        FoundryNoteCard("My Notes", editable=True)  # rich-text area

    For a static list of reminder lines, pass `lines`
    instead of `body`.
    """

    def __init__(
        self,
        title: str,
        body: str = "",
        lines: list[str] | None = None,
        editable: bool = False,
        show_watermark: bool = True,
        parent=None,
    ):
        super().__init__(parent)

        self.setProperty(
            "foundryNoteCard",
            True,
        )

        root = QVBoxLayout(self)

        root.setContentsMargins(14, 12, 14, 14)

        root.setSpacing(8)

        header_row = QHBoxLayout()

        self.title_label = QLabel(
            title.upper()
        )

        self.title_label.setProperty(
            "noteCardTitle",
            True,
        )

        self.title_label.setFont(
            Fonts.label()
        )

        header_row.addWidget(self.title_label)

        header_row.addStretch()

        if show_watermark:

            mark = FoundryIcon(
                "achievement",
                size=Metrics.ICON_SMALL,
                color=Colors.PAPER_BORDER,
            )

            header_row.addWidget(mark)

        root.addLayout(header_row)

        self.editable = editable

        if editable:

            self.text_edit = QTextEdit()

            self.text_edit.setProperty(
                "noteCardBody",
                True,
            )

            self.text_edit.setFont(
                Fonts.note()
            )

            self.text_edit.setPlaceholderText(
                "Take notes here..."
            )

            if body:
                self.text_edit.setPlainText(body)

            root.addWidget(self.text_edit)

        elif lines:

            for line in lines:

                line_label = QLabel(f"• {line}")

                line_label.setWordWrap(True)

                line_label.setProperty(
                    "noteCardBody",
                    True,
                )

                line_label.setFont(
                    Fonts.note()
                )

                root.addWidget(line_label)

        else:

            self.body_label = QLabel(body)

            self.body_label.setWordWrap(True)

            self.body_label.setProperty(
                "noteCardBody",
                True,
            )

            self.body_label.setFont(
                Fonts.note()
            )

            root.addWidget(self.body_label)

    # --------------------------------------------------
    # Public API
    # --------------------------------------------------

    def text(self) -> str:

        if self.editable:
            return self.text_edit.toPlainText()

        return getattr(self.body_label, "text", lambda: "")()

    def set_text(self, text: str):

        if self.editable:
            self.text_edit.setPlainText(text)

        elif hasattr(self, "body_label"):
            self.body_label.setText(text)
