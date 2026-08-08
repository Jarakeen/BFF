from __future__ import annotations

import platform
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QPushButton,
    QLabel,
    QTreeWidget,
    QTreeWidgetItem,
)

from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar   

from ui.components.foundry_card import FoundryCard

class DebugPage(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.build_ui()
        self.connect_signals()

        self.refresh()

    def build_ui(self):

        self.header = FoundryHeader(
            title="Developer Console",
            subtitle="Diagnostics and maintenance.",
            department="Engineering",
        )

        self.widget_tree = QTreeWidget()

        self.widget_tree.setHeaderLabel(
            "Widget Tree"
        )

        self.system_info = QTextEdit()

        self.system_info.setReadOnly(True)

        self.log_output = QTextEdit()

        self.log_output.setReadOnly(True)

        self.refresh_button = QPushButton(
            "Refresh"
        )

        self.dump_button = QPushButton(
            "Dump Widget Tree"
        )

        self.reload_theme = QPushButton(
            "Reload Theme"
        )

        self.reload_settings = QPushButton(
            "Reload Settings"
        )

        self.status = FoundryStatusBar()

        layout = QVBoxLayout(self)

        layout.addWidget(self.header)

        #
        # Top row
        #

        top = QHBoxLayout()

        info = FoundryCard("Application")

        info.addWidget(self.system_info)

        tree = FoundryCard("Widgets")

        tree.addWidget(self.widget_tree)

        top.addWidget(info,1)

        top.addWidget(tree,2)

        layout.addLayout(top)

        #
        # Logs
        #

        logs = FoundryCard("Recent Log")

        logs.addWidget(self.log_output)

        layout.addWidget(logs)

        #
        # Buttons
        #

        buttons = QHBoxLayout()

        buttons.addWidget(self.refresh_button)

        buttons.addWidget(self.dump_button)

        buttons.addWidget(self.reload_theme)

        buttons.addWidget(self.reload_settings)

        buttons.addStretch()

        layout.addLayout(buttons)

        layout.addWidget(self.status)    

    def connect_signals(self):

        self.refresh_button.clicked.connect(
            self.refresh
        )

        self.dump_button.clicked.connect(
            self.dump_tree
        )    

    def refresh(self):

        text = []

        text.append(f"Python : {platform.python_version()}")

        text.append(f"Qt      : {sys.modules['PySide6'].__version__}")

        text.append(f"Platform: {platform.platform()}")

        self.system_info.setPlainText(
            "\n".join(text)
        )

        self.refresh_tree()    

    def refresh_tree(self):

        self.widget_tree.clear()

        window = self.window()

        root = QTreeWidgetItem(
            [window.__class__.__name__]
        )

        self.widget_tree.addTopLevelItem(root)

        self.add_children(
            root,
            window,
        )

        self.widget_tree.expandAll()    

    def add_children(
            self,
            parent_item,
            widget,
        ):

            from PySide6.QtWidgets import QWidget

            children = widget.findChildren(
                QWidget,
                options=Qt.FindDirectChildrenOnly,
            )

            for child in children:

                item = QTreeWidgetItem(
                    [child.__class__.__name__]
                )

                parent_item.addChild(item)

                self.add_children(
                    item,
                    child,
                )   

    def dump_tree(self):

        self.window().dumpObjectTree()

        self.status.success(
            "Widget tree written to console."
        )             