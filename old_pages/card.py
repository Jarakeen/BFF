# widget/card.py

from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QVBoxLayout,

    )

class Card(QFrame):

    def __init__(self, title="", parent=None):
        super().__init__(parent)

        self.setObjectName("card")

        self.title = QLabel(title)
        self.title.setObjectName("cardTitle")

        self.content = QVBoxLayout()

        layout = QVBoxLayout(self)
        layout.addWidget(self.title)
        layout.addLayout(self.content)

    def addWidget(self, widget):
        self.content.addWidget(widget)

    def addLayout(self, layout):
        self.content.addLayout(layout)