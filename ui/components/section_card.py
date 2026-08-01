from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QVBoxLayout,
)

from ui.theme.fonts import Fonts


class SectionCard(QFrame):

    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)

        self.setProperty("sectionCard", True)

        self.title = QLabel(title)
        self.title.setProperty("sectionTitle", True)
        self.title.setFont(Fonts.section())

        self.body = QVBoxLayout()
        self.body.setContentsMargins(20, 16, 20, 20)
        self.body.setSpacing(16)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 10, 18, 18)
        layout.setSpacing(12)

        layout.addWidget(self.title)
        layout.addLayout(self.body)