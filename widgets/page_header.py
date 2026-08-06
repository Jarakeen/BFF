# ==================================================
# Black Feather Foundry
#
# File:
# ui/widgets/page_header.py
# widgets/page_header.py
# Purpose:
# Standard page header used throughout the Foundry.
#
# ==================================================

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QFrame,
    QHBoxLayout,
    QVBoxLayout,
)


class PageHeader(QWidget):
    """
    Standard page header for Foundry pages.

    Example
    -------
    Archive
    Browse imported records.

                               Archives Division
    --------------------------------------------------
    """

    def __init__(
        self,
        title: str,
        subtitle: str = "",
        department: str = "",
        parent=None,
    ):
        super().__init__(parent)

        # --------------------------------------------------
        # Labels
        # --------------------------------------------------

        self.title_label = QLabel(title)
        self.subtitle_label = QLabel(subtitle)
        self.department_label = QLabel(department)

        self.title_label.setObjectName("pageTitle")
        self.subtitle_label.setObjectName("pageSubtitle")
        self.department_label.setObjectName("pageDepartment")

        self.department_label.setAlignment(
            Qt.AlignmentFlag.AlignRight
        )

        # --------------------------------------------------
        # Left Column
        # --------------------------------------------------

        left_layout = QVBoxLayout()
        left_layout.setSpacing(2)

        left_layout.addWidget(self.title_label)
        left_layout.addWidget(self.subtitle_label)

        # --------------------------------------------------
        # Right Column
        # --------------------------------------------------

        right_layout = QVBoxLayout()
        right_layout.addStretch()
        right_layout.addWidget(self.department_label)

        # --------------------------------------------------
        # Header Row
        # --------------------------------------------------

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        header_layout.addLayout(left_layout)
        header_layout.addStretch()
        header_layout.addLayout(right_layout)

        # --------------------------------------------------
        # Divider
        # --------------------------------------------------

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFrameShadow(QFrame.Shadow.Sunken)

        # --------------------------------------------------
        # Main Layout
        # --------------------------------------------------

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addLayout(header_layout)
        layout.addWidget(divider)

    # --------------------------------------------------
    # Public API
    # --------------------------------------------------

    def set_title(self, text: str):
        self.title_label.setText(text)

    def set_subtitle(self, text: str):
        self.subtitle_label.setText(text)

    def set_department(self, text: str):
        self.department_label.setText(text)

    def set_header(
        self,
        title: str,
        subtitle: str = "",
        department: str = "",
    ):
        """
        Update all header text at once.
        """
        self.set_title(title)
        self.set_subtitle(subtitle)
        self.set_department(department)