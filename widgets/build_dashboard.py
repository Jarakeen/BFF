from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QVBoxLayout, QWidget

from widgets.build_editor import BuildEditor


class BuildDashboard(QWidget):
    """Compact card-grid presentation for an existing BuildEditor."""

    def __init__(self, editor: BuildEditor, parent=None):
        super().__init__(parent)

        self.editor = editor
        self.editor.setParent(self)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        content = QWidget()
        content.setMaximumWidth(1480)

        grid = QGridLayout(content)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)

        cards = self._detach_cards()

        # Existing BuildEditor card order:
        # 0 = Identity
        # 1 = Gear
        # 2 = Champion Points
        # 3 = Skills
        # 4 = Boss Alternates

        if len(cards) >= 1:
            grid.addWidget(cards[0], 0, 0, 1, 1)

        if len(cards) >= 2:
            grid.addWidget(cards[1], 0, 1, 2, 1)

        if len(cards) >= 3:
            grid.addWidget(cards[2], 1, 0, 1, 1)

        if len(cards) >= 4:
            grid.addWidget(cards[3], 2, 0, 1, 2)

        if len(cards) >= 5:
            grid.addWidget(cards[4], 3, 0, 1, 2)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        outer.addWidget(
            content,
            0,
            Qt.AlignmentFlag.AlignHCenter
            | Qt.AlignmentFlag.AlignTop,
        )

        outer.addStretch(1)

    def _detach_cards(self) -> list[QWidget]:
        """Move the existing BuildEditor cards into the dashboard grid."""

        layout = self.editor.layout()
        cards: list[QWidget] = []

        if layout is None:
            return cards

        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()

            if widget is not None:
                widget.setParent(self)
                cards.append(widget)

        return cards