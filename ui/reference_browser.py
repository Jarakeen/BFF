# ui/reference_browser.py
"""Reference data browser window."""

from __future__ import annotations

import json
from typing import Any
from services.validation_service import ValidationService
from engine.data_miner import DataBuilderService

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
    QPushButton,
    QListWidget,
    QTableView,
    QApplication,
    QMessageBox,
    QWidget,
    QModelIndex,
    QAbstractTableModel
    
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


    def _build_reference_browser_page(self) -> QWidget:
            page = QWidget()
            layout = QVBoxLayout(page)
    
            title = QLabel("Composition Engine")
            title.setStyleSheet("font-size: 18px; font-weight: bold;")
            layout.addWidget(title)
    
            self.reference_library = ReferenceLibrary(str(Path(__file__).resolve().parents[1] / "data" / "processed"))
            self.reference_data_page = QWidget()
            self.reference_data_layout = QVBoxLayout(self.reference_data_page)
    
            controls = QHBoxLayout()
            self.reference_search_edit = QLineEdit()
            self.reference_search_edit.setPlaceholderText("Search by name")
            self.reference_search_edit.textChanged.connect(self._refresh_reference_data_view)
    
            refresh_btn = QPushButton("Refresh")
            refresh_btn.clicked.connect(self._reload_reference_library)
            controls.addWidget(self.reference_search_edit, 1)
            controls.addWidget(refresh_btn)
            self.reference_data_layout.addLayout(controls)
    
            explorer_splitter = QSplitter(Qt.Orientation.Horizontal)
            explorer_splitter.setChildrenCollapsible(False)
    
            left_panel = QWidget()
            left_layout = QVBoxLayout(left_panel)
            left_layout.setContentsMargins(0, 0, 0, 0)
            self.reference_dataset_list = QListWidget()
            self.reference_dataset_list.currentRowChanged.connect(self._populate_reference_dataset)
            left_layout.addWidget(self.reference_dataset_list)
            explorer_splitter.addWidget(left_panel)
    
            right_panel = QWidget()
            right_layout = QVBoxLayout(right_panel)
            right_layout.setContentsMargins(8, 0, 0, 0)
            self.reference_table = QTableView()
            self.reference_table.setAlternatingRowColors(True)
            self.reference_table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
            self.reference_table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
            self.reference_table.clicked.connect(self._show_reference_row_details)
            self.reference_table.setSortingEnabled(True)
            right_layout.addWidget(self.reference_table)
    
            self.reference_inspector = QTextEdit()
            self.reference_inspector.setReadOnly(True)
            self.reference_inspector.setPlaceholderText("Select a row to inspect the full JSON object.")
            right_layout.addWidget(self.reference_inspector)
            explorer_splitter.addWidget(right_panel)
            explorer_splitter.setSizes([260, 760])
            self.reference_data_layout.addWidget(explorer_splitter, 1)
    
            relationship_panel = QWidget()
            relationship_layout = QVBoxLayout(relationship_panel)
            relationship_layout.setContentsMargins(0, 12, 0, 0)
            relationship_title = QLabel("Relationship Explorer")
            relationship_title.setStyleSheet("font-size: 14px; font-weight: bold;")
            relationship_layout.addWidget(relationship_title)
    
            relationship_controls = QHBoxLayout()
            self.relationship_query_edit = QLineEdit()
            self.relationship_query_edit.setPlaceholderText("Search for an effect like Major Courage")
            self.relationship_query_edit.returnPressed.connect(self._run_relationship_query)
            relationship_run_btn = QPushButton("Query")
            relationship_run_btn.clicked.connect(self._run_relationship_query)
            relationship_controls.addWidget(self.relationship_query_edit, 1)
            relationship_controls.addWidget(relationship_run_btn)
            relationship_layout.addLayout(relationship_controls)
    
            self.relationship_output = QTextEdit()
            self.relationship_output.setReadOnly(True)
            self.relationship_output.setPlaceholderText("Relationship results will appear here.")
            relationship_layout.addWidget(self.relationship_output, 1)
            self.reference_data_layout.addWidget(relationship_panel)
    
            layout.addWidget(self.reference_data_page)
            self._build_reference_data_explorer()
            return page
        

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

    def _dataset_key_from_label(self, item_text: str) -> str:
        normalized = item_text.split(" (")[0].strip().casefold().replace(" ", "_")
        mapping = {
            "skills": "skills",
            "gear_sets": "gear_sets",
            "champion_points": "champion_points",
            "foods": "foods",
            "potions": "potions",
            "encounters": "encounters",
            "mechanics": "mechanics",
            "buff": "buff",
            "debuffs": "debuffs",
            "status_effects": "status_effects",
            "races": "races",
            "guild_passives": "guild_passives",
            "weapon_passives": "weapon_passives",
            "armor_passives": "armor_passives",
        }
        return mapping.get(normalized, normalized)

    def _build_reference_data_explorer(self) -> None:
        self.reference_dataset_list.clear()
        self.reference_model = ReferenceDataTableModel([])
        self.reference_table.setModel(self.reference_model)

        dataset_names = [
            "skills",
            "gear_sets",
            "champion_points",
            "foods",
            "potions",
            "encounters",
            "mechanics",
            "buff",
            "debuffs",
            "status_effects",
            "races",
            "guild_passives",
            "weapon_passives",
            "armor_passives",
        ]

        for dataset_name in dataset_names:
            try:
                data = self.reference_library.get_data(dataset_name)
                records = self.reference_library._records(data)
            except Exception as exc:
                records = []
                self.reference_dataset_list.addItem(f"{dataset_name} (error: {exc})")
                continue

            count = len(records)
            label = f"{dataset_name.replace('_', ' ').title()} ({count})"
            self.reference_dataset_list.addItem(label)

        if self.reference_dataset_list.count() > 0:
            self.reference_dataset_list.setCurrentRow(0)

    def _populate_reference_dataset(self, row: int) -> None:
        if row < 0:
            self.reference_inspector.clear()
            self.reference_model.set_records([])
            return

        item_text = self.reference_dataset_list.item(row).text()
        dataset_key = self._dataset_key_from_label(item_text)
        try:
            data = self.reference_library.get_data(dataset_key)
            records = self.reference_library._records(data)
        except Exception as exc:
            self.reference_model.set_records([])
            self.reference_inspector.setPlainText(f"Loading failed: {exc}")
            return

        filtered = []
        query = self.reference_search_edit.text().strip().casefold()
        for record in records:
            if not isinstance(record, dict):
                continue
            name = str(record.get("name", "")).casefold()
            if not query or query in name:
                filtered.append(record)

        self.reference_model.set_records(filtered)
        self.reference_table.resizeColumnsToContents()
        if filtered:
            self.reference_inspector.setPlainText("No selection yet. Select a row to inspect its JSON object.")
        else:
            self.reference_inspector.setPlainText("No Records")

    def _refresh_reference_data_view(self) -> None:
        current_row = self.reference_dataset_list.currentRow()
        if current_row >= 0:
            self._populate_reference_dataset(current_row)

    def _reload_reference_library(self) -> None:
        try:
            self.reference_library = ReferenceLibrary(str(Path(__file__).resolve().parents[1] / "data" / "processed"))
            self._build_reference_data_explorer()
            self.reference_inspector.setPlainText("ReferenceLibrary reloaded.")
        except Exception as exc:
            self.reference_inspector.setPlainText(f"Reload failed: {exc}")

    def _show_reference_row_details(self, index: QModelIndex) -> None:
        if not index.isValid():
            return
        record = self.reference_model._records[index.row()]
        self.reference_inspector.setPlainText(json.dumps(record, ensure_ascii=False, indent=2, default=str))

    def _run_relationship_query(self) -> None:
        effect = self.relationship_query_edit.text().strip()
        if not effect:
            self.relationship_output.setPlainText("Enter an effect name to search.")
            return
        try:
            result = self.reference_library.find_everything_using(effect)
            lines = [f"Effect: {effect}", ""]
            providers = result.get("providers", [])
            encounters = result.get("encounters", [])
            mechanics = result.get("mechanics", [])

            lines.append(f"Providers ({len(providers)}):")
            for provider in providers[:20]:
                lines.append(f"- {provider.get('name', 'Unnamed')} [{provider.get('source_layer', 'unknown')}]")
            if len(providers) > 20:
                lines.append(f"- ... {len(providers) - 20} more")

            lines.append("")
            lines.append(f"Encounters requiring it ({len(encounters)}):")
            for item in encounters[:20]:
                lines.append(f"- {item.get('name', 'Unnamed')}")
            if len(encounters) > 20:
                lines.append(f"- ... {len(encounters) - 20} more")

            lines.append("")
            lines.append(f"Mechanics requiring it ({len(mechanics)}):")
            for item in mechanics[:20]:
                lines.append(f"- {item.get('name', 'Unnamed')}")
            if len(mechanics) > 20:
                lines.append(f"- ... {len(mechanics) - 20} more")

            self.relationship_output.setPlainText("\n".join(lines))
        except Exception as exc:
            self.relationship_output.setPlainText(f"Relationship query failed: {exc}")

class ReferenceDataTableModel(QAbstractTableModel):
    def __init__(self, records: list[dict] | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._records: list[dict] = records or []
        self._headers: list[str] = []

    def set_records(self, records: list[dict]) -> None:
        self.beginResetModel()
        self._records = records
        self._headers = self._collect_headers(records)
        self.endResetModel()

    def _collect_headers(self, records: list[dict]) -> list[str]:
        columns: set[str] = set()
        for record in records:
            if isinstance(record, dict):
                columns.update(record.keys())
        return sorted(columns)

    def rowCount(self, parent: QModelIndex | None = None) -> int:
        return len(self._records)

    def columnCount(self, parent: QModelIndex | None = None) -> int:
        return len(self._headers)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return self._headers[section] if section < len(self._headers) else ""
        return str(section + 1)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or role not in {Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.ToolTipRole}:
            return None
        record = self._records[index.row()]
        if not isinstance(record, dict):
            return None
        key = self._headers[index.column()]
        value = record.get(key)
        if value is None:
            return ""
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False, default=str)
        return str(value)

        
def rebuild_database(self) -> None:
        self.status_label.setText("Rebuilding database files...")
        QApplication.processEvents()
        try:
            database_path = Path(__file__).resolve().parents[1] / "data" / "processed"
            builder = DataBuilderService(database_path)
            results = builder.build_all()
            validator = ValidationService(database_path)
            report = validator.validate_directory()
            summary = report["summary"]
            message = (
                f"Database rebuilt: {' | '.join(results)} | "
                f"records={summary['total_records']} files={summary['present_files']} "
                f"issues={len(report['issues'])}"
            )
            self.status_label.setText(message)
            QMessageBox.information(self, "Database Rebuild", message)
        except Exception as exc:  # pragma: no cover - UI path guard
            self.status_label.setText(f"Database rebuild failed: {exc}")
            QMessageBox.critical(self, "Database Rebuild", str(exc))

