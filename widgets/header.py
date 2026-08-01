from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QHBoxLayout,
    QVBoxLayout,
)

class Header(QWidget):

    def __init__(self, title, subtitle="", department=""):
        super().__init__()

        # Create labels
        self.title_label = QLabel(title)
        self.subtitle_label = QLabel(subtitle)
        self.department_label = QLabel(department)

        # Left side
        left_layout = QVBoxLayout()
        left_layout.addWidget(self.title_label)
        left_layout.addWidget(self.subtitle_label)

        # Right side
        right_layout = QVBoxLayout()
        right_layout.addWidget(self.department_label)

        # Main layout
        layout = QHBoxLayout(self)
        layout.addLayout(left_layout)
        layout.addStretch()
        layout.addLayout(right_layout)