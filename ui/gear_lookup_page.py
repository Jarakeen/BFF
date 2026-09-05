from __future__ import annotations

import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from engine.config import get_data_dir
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar
from ui.foundry_page import FoundryPage


class GearLookupPage(FoundryPage):
    """Read-only browser for the canonical ESO gear-set catalog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.database_path = get_data_dir() / "eso.db"
        self._sets: list[tuple[int, str, str, int | None]] = []
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        self.header = FoundryHeader(
            title="Gear Lookup",
            subtitle="Find a set quickly, inspect its canonical piece bonuses, and get back to the actual problem.",
            department="TOOLS • GEAR LOOKUP",
        )
        self.set_header(self.header)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search set name, category, or bonus text...")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._filter_sets)
        self.header.add_context_widget(self._context_field("SEARCH", self.search))

        self.category = QComboBox()
        self.category.addItem("All Categories", "")
        self.category.currentIndexChanged.connect(self._filter_sets)
        self.header.add_context_widget(self._context_field("CATEGORY", self.category))

        workspace = QHBoxLayout()
        workspace.setContentsMargins(0, 0, 0, 0)
        workspace.setSpacing(8)

        index_card = FoundryCard("Gear Sets", "⌕").set_watermark("compass", 0.04)
        self.results = QListWidget()
        self.results.currentItemChanged.connect(self._show_selected)
        index_card.addWidget(self.results)
        workspace.addWidget(index_card, 2)

        detail_card = FoundryCard("Set Details", "✦").set_watermark("compass", 0.05)
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

    @staticmethod
    def _context_field(title: str, widget: QWidget) -> QWidget:
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        label = QLabel(title)
        label.setProperty("sidebarHeading", True)
        layout.addWidget(label)
        layout.addWidget(widget)
        return box

    def refresh(self) -> None:
        try:
            with sqlite3.connect(self.database_path) as connection:
                rows = connection.execute(
                    """
                    SELECT id, name, COALESCE(category, ''), max_equip_count
                    FROM gear_set
                    ORDER BY name COLLATE NOCASE
                    """
                ).fetchall()
        except sqlite3.Error as exc:
            self._sets = []
            self.results.clear()
            self.status.error(f"Gear catalog unavailable: {exc}")
            return

        self._sets = [
            (int(set_id), str(name), str(category or ""), max_equip_count)
            for set_id, name, category, max_equip_count in rows
        ]

        selected_category = self.category.currentData()
        categories = sorted({category for _, _, category, _ in self._sets if category}, key=str.casefold)
        self.category.blockSignals(True)
        self.category.clear()
        self.category.addItem("All Categories", "")
        for category in categories:
            self.category.addItem(category, category)
        if selected_category:
            index = self.category.findData(selected_category)
            if index >= 0:
                self.category.setCurrentIndex(index)
        self.category.blockSignals(False)

        self._filter_sets()
        self.status.info(f"Gear Lookup ready • {len(self._sets)} canonical set(s) loaded.")

    def _matching_set_ids_for_bonus_text(self, query: str) -> set[int]:
        if not query:
            return set()
        try:
            with sqlite3.connect(self.database_path) as connection:
                rows = connection.execute(
                    """
                    SELECT DISTINCT set_id
                    FROM gear_set_bonus
                    WHERE description LIKE ? COLLATE NOCASE
                    """,
                    (f"%{query}%",),
                ).fetchall()
        except sqlite3.Error:
            return set()
        return {int(row[0]) for row in rows}

    def _filter_sets(self, *_args) -> None:
        query = self.search.text().strip().casefold() if hasattr(self, "search") else ""
        category = str(self.category.currentData() or "") if hasattr(self, "category") else ""
        bonus_matches = self._matching_set_ids_for_bonus_text(query) if query else set()

        current_id = None
        current = self.results.currentItem() if hasattr(self, "results") else None
        if current is not None:
            current_id = current.data(Qt.ItemDataRole.UserRole)

        self.results.blockSignals(True)
        self.results.clear()
        matched = 0
        restore_row = -1
        for set_id, name, set_category, _max_equip_count in self._sets:
            if category and set_category != category:
                continue
            haystack = f"{name} {set_category}".casefold()
            if query and query not in haystack and set_id not in bonus_matches:
                continue
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, set_id)
            item.setToolTip(set_category or "Uncategorized")
            self.results.addItem(item)
            if set_id == current_id:
                restore_row = matched
            matched += 1
        self.results.blockSignals(False)

        if restore_row >= 0:
            self.results.setCurrentRow(restore_row)
        elif self.results.count():
            self.results.setCurrentRow(0)
        else:
            self.set_name.setText("No matching gear sets")
            self.set_meta.clear()
            self.bonuses.clear()

    def _show_selected(self, current: QListWidgetItem | None, _previous=None) -> None:
        if current is None:
            return
        set_id = current.data(Qt.ItemDataRole.UserRole)
        selected = next((row for row in self._sets if row[0] == set_id), None)
        if selected is None:
            return

        _set_id, name, category, max_equip_count = selected
        try:
            with sqlite3.connect(self.database_path) as connection:
                rows = connection.execute(
                    """
                    SELECT piece_count, description
                    FROM gear_set_bonus
                    WHERE set_id = ?
                    ORDER BY piece_count, id
                    """,
                    (set_id,),
                ).fetchall()
        except sqlite3.Error as exc:
            rows = []
            self.status.error(f"Could not load bonuses for {name}: {exc}")

        self.set_name.setText(name.upper())
        category_text = category or "Uncategorized"
        equip_text = str(max_equip_count) if max_equip_count is not None else "—"
        self.set_meta.setText(f"Category: {category_text}   •   Maximum equipped pieces: {equip_text}")

        if rows:
            lines = []
            for piece_count, description in rows:
                pieces = f"{piece_count} item" if int(piece_count) == 1 else f"{piece_count} items"
                lines.append(f"{pieces}: {description}")
            self.bonuses.setText("\n\n".join(lines))
        else:
            self.bonuses.setText("No canonical piece-bonus records are available for this set.")
