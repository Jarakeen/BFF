# ui/components/section_card.py

from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QLayout,
    QVBoxLayout,
)

from ui.theme.fonts import Fonts


class SectionCard(QFrame):
    """
    Standard Foundry section container.
    """

    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)

        self.setProperty("sectionCard", True)

        self.title = QLabel(title)
        self.title.setProperty("sectionTitle", True)
        self.title.setFont(Fonts.section())

        self.body = QVBoxLayout()
        self.body.setContentsMargins(20, 0, 20, 0)
        self.body.setSpacing(8)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 0, 18, 0)
        layout.setSpacing(6)

        layout.addWidget(self.title)
        layout.addLayout(self.body)

    # --------------------------------------------------
    # Convenience API
    # --------------------------------------------------

    def addWidget(self, widget):
        """Add a widget to the card body."""
        self.body.addWidget(widget)

    def addLayout(self, layout: QLayout):
        """Add a layout to the card body."""
        self.body.addLayout(layout)

    def addStretch(self, stretch: int = 0):
        """Add stretch to the card body."""
        self.body.addStretch(stretch)

    def clear(self):
        """Remove all widgets from the card."""
        while self.body.count():
            item = self.body.takeAt(0)

            if item.widget():
                item.widget().deleteLater()