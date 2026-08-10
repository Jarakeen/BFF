# ==================================================
# Black Feather Foundry
#
# File:
# ui/components/foundry_sidebar.py
#
# Purpose:
# Primary navigation and status panel.
#
# ==================================================

from __future__ import annotations

from PySide6.QtCore import Qt, Signal

from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QFrame,
    QScrollArea,
    QSizePolicy,
)

from ui.components.foundry_button import (
    FoundryButton,
)
from ui.theme.fonts import Fonts


class FoundrySidebar(QWidget):

    pageRequested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.build_ui()

    # --------------------------------------------------
    # UI
    # --------------------------------------------------

    def build_ui(self):

        self.setProperty(
            "foundrySidebar",
            True,
        )

        # --------------------------------------------------
        # Sidebar shell
        #
        # The logo and footer stay fixed. Everything between
        # them is allowed to scroll when the window gets short.
        # --------------------------------------------------

        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            18,
            20,
            18,
            20,
        )

        layout.setSpacing(12)

        #
        # Logo
        #

        logo = QLabel(
            "BLACK FEATHER FOUNDRY"
        )

        logo.setFont(
            Fonts.logo()
        )

        logo.setProperty(
            "sidebarLogo",
            True,
        )

        # Never let the logo be vertically compressed.
        logo.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Fixed,
        )

        logo.setMinimumHeight(
            logo.sizeHint().height()
        )

        layout.addWidget(logo)
        layout.addWidget(self.divider())

        #
        # Scrollable sidebar content
        #

        scroll = QScrollArea()

        scroll.setFrameShape(
            QFrame.Shape.NoFrame
        )

        scroll.setWidgetResizable(True)

        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        content = QWidget()

        content_layout = QVBoxLayout(content)

        content_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        content_layout.setSpacing(12)

        #
        # Navigation
        #

        self.buttons = {}

        pages = [

            ("Broadcast", "broadcast"),
            ("Field Notes", "field_office"),
            ("Live Operations", "live_operations"),
            ("Archive", "archive"),
            ("Incidents", "incident"),
            ("Achievements", "achievement"),
            ("Collections", "collections"),
            ("Roster", "roster"),
            ("Console", "console"),
            ("Settings", "settings"),

        ]

        for text, page in pages:

            button = QPushButton(text)

            button.setProperty(
                "sidebarButton",
                True,
            )

            button.clicked.connect(
                lambda _, p=page:
                    self.pageRequested.emit(p)
            )

            self.buttons[page] = button

            content_layout.addWidget(button)

        content_layout.addStretch()

        content_layout.addWidget(self.divider())

        #
        # Expedition
        #

        self.status_title = QLabel(
            "CURRENT EXPEDITION"
        )

        self.status_title.setProperty(
            "sidebarHeading",
            True,
        )

        content_layout.addWidget(
            self.status_title
        )

        self.current_boss = QLabel(
            "No Expedition"
        )

        self.pull_count = QLabel(
            "Pulls: 0"
        )

        self.best_pull = QLabel(
            "Best: --"
        )

        self.coffee = QLabel(
            "Coffee: --"
        )

        content_layout.addWidget(self.current_boss)
        content_layout.addWidget(self.pull_count)
        content_layout.addWidget(self.best_pull)
        content_layout.addWidget(self.coffee)

        content_layout.addWidget(self.divider())

        #
        # Systems
        #

        systems = QLabel(
            "SYSTEMS"
        )

        systems.setProperty(
            "sidebarHeading",
            True,
        )

        content_layout.addWidget(systems)

        self.obs = QLabel("● OBS")
        self.archive = QLabel("● Archive")
        self.discord = QLabel("● Discord")

        content_layout.addWidget(self.obs)
        content_layout.addWidget(self.archive)
        content_layout.addWidget(self.discord)

        scroll.setWidget(content)

        layout.addWidget(
            scroll,
            1,
        )

        #
        # Footer
        #
        # Kept outside the scroll area so the version number
        # can never disappear when the window is resized.
        #

        footer = QLabel(
            "Black Feather Foundry\\nv1.0"
        )

        footer.setProperty(
            "sidebarFooter",
            True,
        )

        footer.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Fixed,
        )

        footer.setMinimumHeight(
            footer.sizeHint().height()
        )

        layout.addWidget(
            footer
        )

    # --------------------------------------------------
    # Helpers
    # --------------------------------------------------

    def divider(self):

        line = QFrame()

        line.setFrameShape(
            QFrame.Shape.HLine
        )

        line.setProperty(
            "sidebarDivider",
            True,
        )

        return line