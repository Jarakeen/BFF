from __future__ import annotations

_INSTALLED = False


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import (
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QListWidget,
        QSizePolicy,
        QWidget,
    )

    from ui.components.foundry_card import FoundryCard
    from ui.components.foundry_header import FoundryHeader
    from ui.components.foundry_status_bar import FoundryStatusBar
    from ui.gear_lookup_page import GearLookupPage

    def build_compact_ui(self) -> None:
        self.header = FoundryHeader(
            title="Gear Lookup",
            subtitle="Find a set quickly, inspect its canonical piece bonuses, and get back to the actual problem.",
            department="TOOLS • GEAR LOOKUP",
        )
        self.set_header(self.header)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search set name, acquisition, source, or bonus text...")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._filter_sets)

        self.weight = self._filter_combo("All Weights")
        self.bonus = self._filter_combo("Any Bonus")
        self.acquisition_type = self._filter_combo("All Acquisition Types")

        controls = QHBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(8)
        controls.addWidget(self._context_field("SEARCH", self.search), 2)
        controls.addWidget(self._context_field("WEIGHT", self.weight), 1)
        controls.addWidget(self._context_field("BONUS", self.bonus), 1)
        controls.addWidget(self._context_field("ACQUISITION", self.acquisition_type), 1)

        controls_host = QWidget()
        controls_host.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        controls_host.setLayout(controls)
        self.workspace_layout.addWidget(controls_host, 0)

        workspace = QHBoxLayout()
        workspace.setContentsMargins(0, 0, 0, 0)
        workspace.setSpacing(8)

        index_card = FoundryCard("Gear Sets", "search").set_watermark("compass", 0.04)
        self.results = QListWidget()
        self.results.currentItemChanged.connect(self._show_selected)
        index_card.addWidget(self.results)
        workspace.addWidget(index_card, 2)

        detail_card = FoundryCard("Set Details", "set").set_watermark("compass", 0.05)
        self.set_name = QLabel("Select a gear set")
        self.set_name.setProperty("heroTitle", True)
        self.set_meta = QLabel()
        self.set_meta.setWordWrap(True)
        self.bonuses = QLabel()
        self.bonuses.setWordWrap(True)
        self.bonuses.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        detail_card.addWidget(self.set_name)
        detail_card.addWidget(self.set_meta)
        detail_card.addWidget(self.bonuses)
        detail_card.addStretch(1)
        workspace.addWidget(detail_card, 5)

        host = QWidget()
        host.setLayout(workspace)
        self.add_workspace(host)

        self.status = FoundryStatusBar()
        self.set_status(self.status)

    GearLookupPage._build_ui = build_compact_ui
    _INSTALLED = True
