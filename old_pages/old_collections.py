# ui/collections_page.py

from __future__ import annotations


import json
import random
from datetime import datetime
from pathlib import Path
import re



from PySide6.QtCore import Qt, QTimer, QAbstractTableModel, QModelIndex, QSize
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QTableView,
    QTabWidget,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

def _build_odds_and_ends_page(self) -> QWidget:
        page = QWidget()
        outer_layout = QVBoxLayout(page)

        header = QLabel("Collections — Achievements")
        
        outer_layout.addWidget(header)

        search_row = QHBoxLayout()
        self.odds_search_edit = QLineEdit()
        self.odds_search_edit.setPlaceholderText("Search achievements by name...")
        self.odds_search_edit.returnPressed.connect(self.run_odds_search)
        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self.run_odds_search)
        clear_btn = QPushButton("Clear Search")
        clear_btn.clicked.connect(self.clear_odds_search)
        search_row.addWidget(self.odds_search_edit)
        search_row.addWidget(search_btn)
        search_row.addWidget(clear_btn)
        outer_layout.addLayout(search_row)

        sheets_row = QHBoxLayout()
        self.odds_sheets_status_label = QLabel("Google Sheets: not connected")
        connect_sheets_btn = QPushButton("Connect to Google Sheets")
        connect_sheets_btn.clicked.connect(self.connect_google_sheets)
        sheets_row.addWidget(self.odds_sheets_status_label)
        sheets_row.addWidget(connect_sheets_btn)
        sheets_row.addStretch(1)
        outer_layout.addLayout(sheets_row)

        self.odds_progress_label = QLabel(f"Locally marked complete: {self.achievement_progress_service.completed_count()}")
        outer_layout.addWidget(self.odds_progress_label)

        # Master-detail split: category headings on the left act as their own
        # submenu; picking one loads its subcategories/achievements on the right.
        split_row = QHBoxLayout()

        self.odds_category_list = QListWidget()
        self.odds_category_list.setMaximumWidth(240)
        self.odds_category_list.addItems(self.eso_data_service.top_categories())
        self.odds_category_list.currentItemChanged.connect(self.on_odds_category_selected)
        split_row.addWidget(self.odds_category_list)

        detail_column = QVBoxLayout()
        self.odds_category_heading = QLabel("Select a category on the left")
        
        detail_column.addWidget(self.odds_category_heading)

        self.odds_tree = QTreeWidget()
        self.odds_tree.setHeaderLabels(["Achievement", "Points"])
        self.odds_tree.setColumnWidth(0, 380)
        self.odds_tree.itemExpanded.connect(self.on_odds_tree_expanded)
        self.odds_tree.itemChanged.connect(self.on_odds_item_changed)
        detail_column.addWidget(self.odds_tree)

        self.odds_search_results = QTreeWidget()
        self.odds_search_results.setHeaderLabels(["Achievement", "Category", "Points"])
        self.odds_search_results.itemChanged.connect(self.on_odds_item_changed)
        self.odds_search_results.hide()
        detail_column.addWidget(self.odds_search_results)

        split_row.addLayout(detail_column, 1)
        outer_layout.addLayout(split_row)

        return page

def on_odds_category_selected(self, current, previous) -> None:
        if current is None:
            return
        category = current.text()
        self.odds_category_heading.setText(category)
        self._populate_odds_subcategories(category)

def _populate_odds_subcategories(self, category: str) -> None:
        self.odds_tree.blockSignals(True)
        self.odds_tree.clear()
        for subcategory in self.eso_data_service.subcategories(category):
            item = QTreeWidgetItem([subcategory, ""])
            item.setData(0, Qt.ItemDataRole.UserRole, {"kind": "subcategory", "category": category, "subcategory": subcategory})
            item.addChild(QTreeWidgetItem(["Loading...", ""]))  # placeholder so it's expandable
            self.odds_tree.addTopLevelItem(item)
        self.odds_tree.blockSignals(False)

def on_odds_tree_expanded(self, item: QTreeWidgetItem) -> None:
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data.get("kind") != "subcategory" or data.get("loaded"):
            return

        self.odds_tree.blockSignals(True)
        item.takeChildren()
        achievements = self.eso_data_service.achievements_in(data["category"], data["subcategory"])
        for achievement in achievements:
            self._add_achievement_leaf(item, achievement)
        data["loaded"] = True
        item.setData(0, Qt.ItemDataRole.UserRole, data)
        self.odds_tree.blockSignals(False)

def _add_achievement_leaf(self, parent: QTreeWidgetItem, achievement: dict) -> QTreeWidgetItem:
        leaf = QTreeWidgetItem([achievement["name"], str(achievement["points"])])
        leaf.setData(0, Qt.ItemDataRole.UserRole, {"kind": "achievement", "id": achievement["id"], "name": achievement["name"]})
        leaf.setToolTip(0, achievement.get("desc", ""))
        leaf.setFlags(leaf.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        checked = self.achievement_progress_service.is_complete(achievement["id"])
        leaf.setCheckState(0, Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        parent.addChild(leaf)
        return leaf

def run_odds_search(self) -> None:
        query = self.odds_search_edit.text().strip()
        if not query:
            self.clear_odds_search()
            return

        results = self.eso_data_service.search(query)
        self.odds_tree.hide()
        self.odds_search_results.show()
        self.odds_search_results.blockSignals(True)
        self.odds_search_results.clear()
        for result in results:
            item = QTreeWidgetItem([result["name"], f"{result['category']} / {result['subcategory']}", str(result["points"])])
            item.setData(0, Qt.ItemDataRole.UserRole, {"kind": "achievement", "id": result["id"], "name": result["name"]})
            item.setToolTip(0, result.get("desc", ""))
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            checked = self.achievement_progress_service.is_complete(result["id"])
            item.setCheckState(0, Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
            self.odds_search_results.addTopLevelItem(item)
        self.odds_search_results.blockSignals(False)
        self.status_label.setText(f"Found {len(results)} matching achievements")

def clear_odds_search(self) -> None:
        self.odds_search_edit.clear()
        self.odds_search_results.hide()
        self.odds_search_results.clear()
        self.odds_tree.show()

def on_odds_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data.get("kind") != "achievement":
            return

        checked = item.checkState(0) == Qt.CheckState.Checked
        achievement_id = data["id"]
        achievement_name = data["name"]
        self.achievement_progress_service.set_complete(achievement_id, checked)
        self.odds_progress_label.setText(
            f"Locally marked complete: {self.achievement_progress_service.completed_count()}"
        )

        if self.google_sheets_connected:
            try:
                written = self.google_sheets_service.set_status(achievement_name, self.google_sheets_person, checked)
                if written:
                    self.status_label.setText(f"Synced '{achievement_name}' to Google Sheets")
                else:
                    self.status_label.setText(f"'{achievement_name}' not found in your Google Sheet - saved locally only")
            except Exception as exc:  # pragma: no cover - network/auth failures
                self.status_label.setText(f"Google Sheets sync failed: {exc}")

def connect_google_sheets(self) -> None:
        self.odds_sheets_status_label.setText("Google Sheets: building index (this can take a moment)...")
        QApplication.processEvents()
        try:
            count = self.google_sheets_service.build_index()
            self.google_sheets_connected = True
            self.odds_sheets_status_label.setText(f"Google Sheets: connected ({count} achievements indexed)")
        except GoogleSheetsNotConfigured as exc:
            self.google_sheets_connected = False
            self.odds_sheets_status_label.setText(f"Google Sheets: not configured - {exc}")
        except Exception as exc:  # pragma: no cover - network/auth/library failures
            self.google_sheets_connected = False
            self.odds_sheets_status_label.setText(f"Google Sheets: connection failed - {exc}")