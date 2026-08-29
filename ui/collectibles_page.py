# ==================================================
# Black Feather Foundry
#
# File:
# ui/collectibles_page.py
#
# Purpose:
# Dedicated ESO Collectibles browser for the Collections
# sidebar. This page is intentionally separate from the
# existing Achievements pages.
#
# ==================================================

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QLabel,
    QSizePolicy,
)

from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_status_bar import FoundryStatusBar
from services.eso_collectible_database_service import EsoCollectibleDatabaseService


class CollectiblesPage(QWidget):
    """One shared page used by all ``collectibles:*`` routes."""

    DEFAULT_CATEGORY = "Mounts"

    def __init__(self, parent=None):
        super().__init__(parent)
        data_dir = Path(__file__).resolve().parents[1] / "data"
        self.service = EsoCollectibleDatabaseService(data_dir / "eso.db")
        self.category = self.DEFAULT_CATEGORY
        self.build_ui()
        self.connect_signals()
        self.refresh()

    def build_ui(self):
        self.header = FoundryHeader(
            title=self.category,
            subtitle="Browse ESO collectible reference data.",
            department="Collections",
        )

        self.search = QLineEdit()
        self.search.setPlaceholderText(
            "Search this collection by name, description, or subtype..."
        )
        self.search.setClearButtonEnabled(True)
        self.search.setProperty("collectibleSearch", True)

        self.results = QListWidget()
        self.results.setAlternatingRowColors(True)
        self.results.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        self.list_card = FoundryCard(self.category)
        self.list_card.addWidget(self.search)
        self.list_card.addWidget(self.results)

        self.detail_name = QLabel("Select a collectible.")
        self.detail_name.setWordWrap(True)
        self.detail_name.setProperty("collectibleDetailName", True)

        self.detail_type = QLabel("")
        self.detail_type.setWordWrap(True)
        self.detail_type.setProperty("collectibleDetailMeta", True)

        self.detail_description = QLabel("")
        self.detail_description.setWordWrap(True)
        self.detail_description.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self.detail_hint = QLabel("")
        self.detail_hint.setWordWrap(True)
        self.detail_hint.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self.detail_flags = QLabel("")
        self.detail_flags.setWordWrap(True)
        self.detail_flags.setProperty("collectibleDetailMeta", True)

        self.detail_card = FoundryCard("Collectible Details")
        self.detail_card.addWidget(self.detail_name)
        self.detail_card.addWidget(self.detail_type)
        self.detail_card.addWidget(self.detail_description)
        self.detail_card.addWidget(self.detail_hint)
        self.detail_card.addWidget(self.detail_flags)
        self.detail_card.addStretch(1)

        workspace = QHBoxLayout()
        workspace.setContentsMargins(0, 0, 0, 0)
        workspace.setSpacing(12)
        workspace.addWidget(self.list_card, 3)
        workspace.addWidget(self.detail_card, 2)

        self.status = FoundryStatusBar()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)
        layout.addWidget(self.header)
        layout.addLayout(workspace, 1)
        layout.addWidget(self.status)

    def connect_signals(self):
        self.search.textChanged.connect(self.refresh)
        self.results.currentItemChanged.connect(self._selection_changed)

    def set_category(self, category: str):
        if not category:
            category = self.DEFAULT_CATEGORY
        if category == self.category:
            self.refresh()
            return

        self.category = category
        self.header.title.setText(category)
        self.header.subtitle.setText(
            f"Browse ESO {category.lower()} in the collectible catalog."
        )
        self.list_card.set_title(category)
        self.search.clear()
        self._clear_details()
        self.refresh()

    def refresh(self):
        self.results.clear()

        if not self.service.available:
            item = QListWidgetItem(
                self.service.bootstrap_message
                or "Collectible reference data has not been installed."
            )
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.results.addItem(item)
            self.list_card.set_badge("0")
            self.status.warning(
                self.service.bootstrap_message
                or "Collectible reference data is unavailable."
            )
            return

        rows = self.service.collectibles(self.category, self.search.text())
        for row in rows:
            text = row["name"]
            subtype = row.get("source_subcategory_name") or ""
            if subtype:
                text = f"{text}   ·   {subtype}"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, row["id"])
            self.results.addItem(item)

        total = self.service.category_count(self.category)
        self.list_card.set_badge(f"{len(rows):,} / {total:,}")

        if self.search.text().strip():
            self.status.info(f"{len(rows):,} matches in {self.category}.")
        else:
            self.status.info(f"{total:,} collectibles in {self.category}.")

        if rows:
            self.results.setCurrentRow(0)
        else:
            self._clear_details("No collectibles matched this search.")

    def _selection_changed(self, current, _previous):
        if current is None:
            return

        collectible_id = current.data(Qt.ItemDataRole.UserRole)
        if collectible_id is None:
            return

        row = self.service.collectible(int(collectible_id))
        if not row:
            self._clear_details("Collectible details are unavailable.")
            return

        self.detail_name.setText(row.get("name") or "Unnamed Collectible")
        type_name = row.get("canonical_type_name") or row.get("canonical_type_key") or ""
        subtype = row.get("source_subcategory_name") or ""
        self.detail_type.setText(" · ".join(part for part in (type_name, subtype) if part))

        description = (row.get("description") or "").strip()
        self.detail_description.setText(description or "No description is available.")

        hint = (row.get("hint") or "").strip()
        self.detail_hint.setText(f"Acquisition hint: {hint}" if hint else "")

        flags = []
        if row.get("is_usable"):
            flags.append("Usable")
        if row.get("is_renameable"):
            flags.append("Renameable")
        if row.get("is_slottable"):
            flags.append("Slottable")
        if row.get("has_appearance"):
            flags.append("Appearance")
        self.detail_flags.setText(" · ".join(flags))

    def _clear_details(self, message: str = "Select a collectible."):
        self.detail_name.setText(message)
        self.detail_type.clear()
        self.detail_description.clear()
        self.detail_hint.clear()
        self.detail_flags.clear()

    def closeEvent(self, event):
        self.service.close()
        super().closeEvent(event)
