# ui/reference_browser.py
"""Reference data browser window."""

from __future__ import annotations

import json
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QSplitter,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from services.reference_service import ReferenceLibrary



class ReferenceBrowserWindow(QMainWindow):
    """Browse ReferenceLibrary records without changing application state."""

    record_selected = Signal(dict)

    def __init__(self, reference_library: ReferenceLibrary, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.reference_library = reference_library
        self._records_by_category: dict[str, list[dict]] = {}

        self.setWindowTitle("Reference Browser")
        self.resize(1100, 720)
        self._build_ui()
        self._load_records()

    def _build_ui(self) -> None:
        search_label = QLabel("Search references")
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search by name...")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self._on_search_changed)

        search_layout = QVBoxLayout()
        search_layout.setContentsMargins(0, 0, 0, 12)
        search_layout.setSpacing(6)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_edit)

        self.navigation_tree = QTreeWidget()
        self.navigation_tree.setHeaderLabels(["Reference data"])
        self.navigation_tree.setAlternatingRowColors(True)
        self.navigation_tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.navigation_tree.itemSelectionChanged.connect(self._show_selected_record)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.addLayout(search_layout)
        left_layout.addWidget(self.navigation_tree)

        self.detail_title = QLabel("Select a reference record")
        self.detail_title.setFont(QFont("Segoe UI", 14, QFont.Weight.DemiBold))
        self.detail_view = QTextEdit()
        self.detail_view.setReadOnly(True)
        self.detail_view.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.detail_view.setFont(QFont("Consolas", 10))
        self.detail_view.setPlaceholderText("Record details will appear here.")

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(16, 12, 12, 12)
        right_layout.setSpacing(10)
        right_layout.addWidget(self.detail_title)
        right_layout.addWidget(self.detail_view)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([330, 770])
        self.setCentralWidget(splitter)

    def _load_records(self) -> None:
        self._records_by_category.clear()
        for category in sorted(self.reference_library.cache):
            records = self.reference_library._records(
                self.reference_library.get_data(category)
            )
            named_records = [record for record in records if isinstance(record.get("name"), str)]
            if named_records:
                self._records_by_category[category] = sorted(
                    named_records,
                    key=lambda record: record["name"].casefold(),
                )
        self._rebuild_navigation()

    def _rebuild_navigation(self) -> None:
        query = self.search_edit.text().strip().casefold()
        self.navigation_tree.clear()

        first_record: QTreeWidgetItem | None = None
        for category, records in self._records_by_category.items():
            matching_records = [
                record for record in records
                if not query or query in record["name"].casefold()
            ]
            if not matching_records:
                continue

            category_item = QTreeWidgetItem([category.replace("_", " ").title()])
            category_item.setFlags(category_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.navigation_tree.addTopLevelItem(category_item)

            for record in matching_records:
                item = QTreeWidgetItem([record["name"]])
                item.setData(0, Qt.ItemDataRole.UserRole, record)
                category_item.addChild(item)
                first_record = first_record or item

            category_item.setExpanded(True)

        if first_record is not None and not self.navigation_tree.selectedItems():
            self.navigation_tree.setCurrentItem(first_record)
        elif first_record is None:
            self.detail_title.setText("No matching reference records")
            self.detail_view.clear()

    def _on_search_changed(self, _query: str) -> None:
        self._rebuild_navigation()

    def _show_selected_record(self) -> None:
        selected_items = self.navigation_tree.selectedItems()
        if not selected_items:
            return

        record = selected_items[0].data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(record, dict):
            return

        self.detail_title.setText(str(record.get("name", "Reference record")))
        self.detail_view.setPlainText(json.dumps(record, ensure_ascii=False, indent=2, default=str))
        self.record_selected.emit(record)
