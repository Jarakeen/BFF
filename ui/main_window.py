# ==================================================
# Black Feather Foundry
#
# File:
# main_window.py
#
# Purpose:
# Main application window.
#
# ==================================================

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QStackedWidget,
    )

from widgets.sidebar import Sidebar

from ui.broadcast_page import BroadcastPage
from ui.field_notes_page import FieldNotesPage
from ui.stream_elements_page import LiveOperationsPage
from ui.archive_page import ArchivePage
from ui.incident_page import IncidentPage
from ui.achievement_page import AchievementPage
from ui.collections_page import CollectionsPage
from ui.operations_console import OperationsConsole
from ui.settings_page import SettingsPage

class MainWindow(QMainWindow):
    """
    Black Feather Foundry main window.
    """

    def __init__(self):
        super().__init__()

        self.setWindowTitle(
            "Black Feather Foundry Field Office"
        )

        self.resize(
            1700,
            950,
        )

        self.build_ui()

        self.connect_signals()

    # --------------------------------------------------
    # UI
    # --------------------------------------------------

    def build_ui(self):

        #
        # Central Widget
        #

        central = QWidget()

        self.setCentralWidget(
            central
        )

        layout = QHBoxLayout(central)

        layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        layout.setSpacing(0)

        #
        # Sidebar
        #

        self.sidebar = Sidebar()

        layout.addWidget(self.sidebar)
        
        

        #
        # Pages
        #

        self.stack = QStackedWidget()

        layout.addWidget(
            self.stack,
            1,
        )

        #
        # Build Pages
        #

        self.pages = {

            "broadcast": BroadcastPage(),

            "field_office": FieldNotesPage(),

            "live_operations": LiveOperationsPage(),

            "archive": ArchivePage(),

            "incident": IncidentPage(),

            "achievement": AchievementPage(),

            "collections": CollectionsPage(),

            "console": OperationsConsole(),

            "settings": SettingsPage(),

        }      

        for page in self.pages.values():

            self.stack.addWidget(
                page
            )

        self.stack.setCurrentWidget(
            self.pages["broadcast"]
        )

    # --------------------------------------------------
    # Signals
    # --------------------------------------------------

    def connect_signals(self):

        self.sidebar.pageRequested.connect(
            self.show_page
        )

    # --------------------------------------------------
    # Navigation
    # --------------------------------------------------

    def show_page(
        self,
        page_name: str,
    ):

        page = self.pages.get(
            page_name
        )

        if page is None:
            return

        self.stack.setCurrentWidget(
            page
        )