from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTextEdit,
    QPushButton,
    QHBoxLayout,
)
from PySide6.QtCore import Signal
from datetime import datetime


class FieldNotebook(QWidget):

    notesChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.editor = QTextEdit()
        
        self.editor.setPlaceholderText(
            "Capture observations during the expedition..."
        )

       

        self.timestamp = QPushButton(
            "Insert Timestamp"
        )

        self.clear_button = QPushButton(
            "Clear Notes"
        )

        buttons = QHBoxLayout()
        buttons.addWidget(self.timestamp)
        buttons.addStretch()
        buttons.addWidget(self.clear_button)

        layout = QVBoxLayout(self)
        layout.addLayout(buttons)
        layout.addWidget(self.editor)

        self.timestamp.clicked.connect(
            self.insert_timestamp
        )

        self.clear_button.clicked.connect(
            self.editor.clear
        )

        self.editor.textChanged.connect(
            self.notesChanged.emit
        )

    @property
    def text(self):
        return self.editor.toPlainText()

    def clear(self):
        self.editor.clear()

    def insert_timestamp(self):
        stamp = datetime.now().strftime("%H:%M")
        self.editor.append(f"\n[{stamp}] ")