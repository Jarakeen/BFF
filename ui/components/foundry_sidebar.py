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

from PySide6.QtCore import Signal

from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QFrame,
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

        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            18,
            20,
            18,
            20,
        )

        layout.setSpacing(16)

        #
        # Logo
        #

        logo = QLabel(
            "BLACK FEATHER\nFOUNDRY"
        )

        logo.setFont(
            Fonts.logo()
        )

        logo.setProperty(
            "sidebarLogo",
            True,
        )

        layout.addWidget(logo)

        layout.addWidget(self.divider())

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

            layout.addWidget(button)

        layout.addStretch()

        layout.addWidget(self.divider())

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

        layout.addWidget(
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

        layout.addWidget(self.current_boss)
        layout.addWidget(self.pull_count)
        layout.addWidget(self.best_pull)
        layout.addWidget(self.coffee)

        layout.addWidget(self.divider())

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

        layout.addWidget(systems)

        self.obs = QLabel("● OBS")
        self.archive = QLabel("● Archive")
        self.discord = QLabel("● Discord")

        layout.addWidget(self.obs)
        layout.addWidget(self.archive)
        layout.addWidget(self.discord)

        layout.addStretch()

        #
        # Footer
        #

        footer = QLabel(
            "Black Feather Foundry\nv1.0"
        )

        footer.setProperty(
            "sidebarFooter",
            True,
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