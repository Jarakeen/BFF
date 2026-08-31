# ==================================================
# Black Feather Foundry
# ui/collectibles_page.py
# Dedicated ESO Collectibles browser with batch ownership tracking.
# ==================================================

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from engine.config import get_data_dir
from services.collectible_icon_catalog import CollectibleIconCatalog
from services.eso_collectible_database_service import EsoCollectibleDatabaseService
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar


class CollectiblesPage(QWidget):
    """Shared page used by all ``collectibles:*`` routes."""

    DEFAULT_CATEGORY = "Mounts"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.data_dir = get_data_dir()
        self.service = EsoCollectibleDatabaseService(self.data_dir / "eso.db")
        self.icon_catalog = CollectibleIconCatalog(self.data_dir)
        self.category = self.DEFAULT_CATEGORY
        self.current_collectible_id: int | None = None
        self.pending_changes: dict[int, bool] = {}
        self._last_clicked_row: int | None = None
        self._building_results = False
        self.build_ui()
        self.connect_signals()
        self.refresh()

    def build_ui(self):
        self.header = FoundryHeader(
            title=self.category,
            subtitle="Browse ESO collectible reference data and mark ownership in batches.",
            department="Collections",
        )

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search this collection by name, description, or subtype...")
        self.search.setClearButtonEnabled(True)
        self.search.setProperty("collectibleSearch", True)

        self.results = QListWidget()
        self.results.setAlternatingRowColors(True)
        self.results.setIconSize(QSize(42, 42))
        self.results.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.results.setSelectionMode(QListWidget.SelectionMode.SingleSelection)

        self.backup_button = QPushButton("Back Up Collection")
        self.backup_button.setToolTip("Export collection progress as a spreadsheet-compatible CSV backup.")

        pending_bar = QHBoxLayout()
        self.pending_label = QLabel("No pending changes")
        self.pending_label.setProperty("muted", True)
        self.save_batch_button = QPushButton("Save Changes")
        self.save_batch_button.setProperty("primary", True)
        self.save_batch_button.setEnabled(False)
        self.discard_batch_button = QPushButton("Discard Changes")
        self.discard_batch_button.setEnabled(False)
        pending_bar.addWidget(self.pending_label)
        pending_bar.addStretch(1)
        pending_bar.addWidget(self.discard_batch_button)
        pending_bar.addWidget(self.save_batch_button)

        help_text = QLabel("Click a checkbox to mark ownership. Shift-click another checkbox to apply the same state across the whole range.")
        help_text.setWordWrap(True)
        help_text.setProperty("muted", True)

        self.list_card = FoundryCard(self.category)
        self.list_card.set_header_action(self.backup_button)
        self.list_card.addWidget(self.search)
        self.list_card.addWidget(help_text)
        self.list_card.addWidget(self.results)
        self.list_card.addLayout(pending_bar)

        self.detail_icon = QLabel()
        self.detail_icon.setFixedSize(112, 112)
        self.detail_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detail_icon.setProperty("collectibleDetailIcon", True)

        self.detail_name = QLabel("Select a collectible.")
        self.detail_name.setWordWrap(True)
        self.detail_name.setProperty("collectibleDetailName", True)
        self.detail_type = QLabel("")
        self.detail_type.setWordWrap(True)
        self.detail_type.setProperty("collectibleDetailMeta", True)
        self.detail_description = QLabel("")
        self.detail_description.setWordWrap(True)
        self.detail_description.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.detail_hint = QLabel("")
        self.detail_hint.setWordWrap(True)
        self.detail_flags = QLabel("")
        self.detail_flags.setWordWrap(True)
        self.detail_flags.setProperty("collectibleDetailMeta", True)

        self.collected = QCheckBox("Collected")
        self.acquired_on = QLineEdit()
        self.acquired_on.setPlaceholderText("Acquired on (YYYY-MM-DD, optional)")
        self.notes = QLineEdit()
        self.notes.setPlaceholderText("Collection notes (optional)")
        self.save_progress = QPushButton("Save Details")
        self.save_progress.setEnabled(False)

        detail_heading = QHBoxLayout()
        detail_heading.addWidget(self.detail_icon, 0, Qt.AlignmentFlag.AlignTop)
        detail_text = QVBoxLayout()
        detail_text.addWidget(self.detail_name)
        detail_text.addWidget(self.detail_type)
        detail_text.addStretch(1)
        detail_heading.addLayout(detail_text, 1)

        self.detail_card = FoundryCard("Collectible Details")
        self.detail_card.addLayout(detail_heading)
        self.detail_card.addWidget(self.detail_description)
        self.detail_card.addWidget(self.detail_hint)
        self.detail_card.addWidget(self.detail_flags)
        self.detail_card.addWidget(self.collected)
        self.detail_card.addWidget(self.acquired_on)
        self.detail_card.addWidget(self.notes)
        self.detail_card.addWidget(self.save_progress)
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
        self.results.itemClicked.connect(self._ownership_clicked)
        self.save_progress.clicked.connect(self._save_detail_status)
        self.save_batch_button.clicked.connect(self.save_pending_changes)
        self.discard_batch_button.clicked.connect(self.discard_pending_changes)
        self.backup_button.clicked.connect(self._backup_collection)

    def has_pending_changes(self) -> bool:
        return bool(self.pending_changes)

    def set_category(self, category: str):
        category = category or self.DEFAULT_CATEGORY
        if category == self.category:
            self.refresh()
            return
        self.category = category
        self.header.title.setText(category)
        self.header.subtitle.setText(f"Browse ESO {category.lower()} and mark ownership in batches.")
        self.list_card.set_title(category)
        self.search.clear()
        self._last_clicked_row = None
        self._clear_details()
        self.refresh()

    def refresh(self):
        selected_id = self.current_collectible_id
        self._building_results = True
        self.results.clear()

        if not self.service.available:
            item = QListWidgetItem(self.service.bootstrap_message or "Collectible reference data has not been installed.")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.results.addItem(item)
            self.list_card.set_badge("0")
            self._building_results = False
            self.status.warning(self.service.bootstrap_message or "Collectible reference data is unavailable.")
            return

        rows = self.service.collectibles(self.category, self.search.text())
        selected_row = -1
        for index, row in enumerate(rows):
            item = QListWidgetItem(row["name"])
            item.setData(Qt.ItemDataRole.UserRole, row["id"])
            item.setData(Qt.ItemDataRole.UserRole + 1, bool(row.get("owned")))
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            effective = self.pending_changes.get(int(row["id"]), bool(row.get("owned")))
            item.setCheckState(Qt.CheckState.Checked if effective else Qt.CheckState.Unchecked)
            subtype = row.get("source_subcategory_name") or ""
            if subtype:
                item.setText(f"{row['name']}   ·   {subtype}")
            icon_path = self.icon_catalog.path_for(row["id"])
            if icon_path is not None:
                item.setIcon(QIcon(str(icon_path)))
            self.results.addItem(item)
            if selected_id is not None and row["id"] == selected_id:
                selected_row = index

        self._building_results = False
        owned, total = self.service.progress_summary(self.category)
        pending_delta = sum(1 for cid in self.pending_changes if any(
            self.results.item(i).data(Qt.ItemDataRole.UserRole) == cid for i in range(self.results.count())
        ))
        self.list_card.set_badge(f"{owned:,} / {total:,} collected")
        icon_note = f" · {self.icon_catalog.available_count:,} local icons cached" if self.icon_catalog.available_count else ""
        self.status.info(f"{len(rows):,} shown · {owned:,}/{total:,} {self.category.lower()} collected{icon_note} · {pending_delta} pending here.")
        self._update_pending_ui()

        if rows:
            self.results.setCurrentRow(selected_row if selected_row >= 0 else 0)
        else:
            self._clear_details("No collectibles matched this search.")

    def _ownership_clicked(self, item: QListWidgetItem):
        if self._building_results:
            return
        row = self.results.row(item)
        new_state = item.checkState() == Qt.CheckState.Checked
        modifiers = QApplication.keyboardModifiers()
        if modifiers & Qt.KeyboardModifier.ShiftModifier and self._last_clicked_row is not None:
            start, end = sorted((self._last_clicked_row, row))
            self._building_results = True
            for i in range(start, end + 1):
                target = self.results.item(i)
                cid = target.data(Qt.ItemDataRole.UserRole)
                if cid is None:
                    continue
                target.setCheckState(Qt.CheckState.Checked if new_state else Qt.CheckState.Unchecked)
                self._stage_change(int(cid), new_state, bool(target.data(Qt.ItemDataRole.UserRole + 1)))
            self._building_results = False
        else:
            cid = item.data(Qt.ItemDataRole.UserRole)
            if cid is not None:
                self._stage_change(int(cid), new_state, bool(item.data(Qt.ItemDataRole.UserRole + 1)))
        self._last_clicked_row = row
        self._update_pending_ui()

    def _stage_change(self, collectible_id: int, owned: bool, original_owned: bool):
        if owned == original_owned:
            self.pending_changes.pop(collectible_id, None)
        else:
            self.pending_changes[collectible_id] = owned

    def _update_pending_ui(self):
        count = len(self.pending_changes)
        self.pending_label.setText(f"{count} change{'s' if count != 1 else ''} pending" if count else "No pending changes")
        self.save_batch_button.setEnabled(count > 0)
        self.discard_batch_button.setEnabled(count > 0)

    def save_pending_changes(self):
        if not self.pending_changes:
            return
        db = self.service.connection
        try:
            db.execute("BEGIN")
            for collectible_id, owned in self.pending_changes.items():
                existing = self.service.collectible(int(collectible_id)) or {}
                acquired_on = existing.get("acquired_on") or None
                notes = existing.get("notes") or ""
                db.execute(
                    """
                    INSERT INTO collectible_progress (collectible_id, owned, acquired_on, notes, updated_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(collectible_id) DO UPDATE SET
                        owned = excluded.owned,
                        acquired_on = excluded.acquired_on,
                        notes = excluded.notes,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (int(collectible_id), 1 if owned else 0, acquired_on, notes),
                )
            db.commit()
        except Exception:
            db.rollback()
            raise
        count = len(self.pending_changes)
        self.pending_changes.clear()
        self._last_clicked_row = None
        self.status.success(f"Saved {count} collectible ownership change{'s' if count != 1 else ''} in one transaction.")
        self.refresh()

    def discard_pending_changes(self):
        self.pending_changes.clear()
        self._last_clicked_row = None
        self.status.info("Pending collectible changes discarded.")
        self.refresh()

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
        self.current_collectible_id = int(collectible_id)
        self._set_detail_icon(self.current_collectible_id)
        self.detail_name.setText(row.get("name") or "Unnamed Collectible")
        type_name = row.get("canonical_type_name") or row.get("canonical_type_key") or ""
        subtype = row.get("source_subcategory_name") or ""
        self.detail_type.setText(" · ".join(part for part in (type_name, subtype) if part))
        self.detail_description.setText((row.get("description") or "").strip() or "No description is available.")
        hint = (row.get("hint") or "").strip()
        self.detail_hint.setText(f"Acquisition hint: {hint}" if hint else "")
        flags = []
        if row.get("is_usable"): flags.append("Usable")
        if row.get("is_renameable"): flags.append("Renameable")
        if row.get("is_slottable"): flags.append("Slottable")
        if row.get("has_appearance"): flags.append("Appearance")
        self.detail_flags.setText(" · ".join(flags))
        effective = self.pending_changes.get(self.current_collectible_id, bool(row.get("owned")))
        self.collected.setChecked(effective)
        self.acquired_on.setText(row.get("acquired_on") or "")
        self.notes.setText(row.get("notes") or "")
        self.save_progress.setEnabled(True)

    def _save_detail_status(self):
        if self.current_collectible_id is None:
            return
        self.service.set_progress(
            self.current_collectible_id,
            owned=self.collected.isChecked(),
            acquired_on=self.acquired_on.text(),
            notes=self.notes.text(),
        )
        self.pending_changes.pop(self.current_collectible_id, None)
        self.status.success("Collectible details saved.")
        self.refresh()

    def _backup_collection(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.data_dir / "backups" / f"collectibles_{timestamp}.csv"
        try:
            path = self.service.export_progress_csv(backup_path)
        except Exception as exc:
            self.status.warning(f"Collection backup failed: {exc}")
            return
        self.status.info(f"Collection backup saved: {path}")

    def _set_detail_icon(self, collectible_id: int) -> None:
        self.detail_icon.clear()
        icon_path = self.icon_catalog.path_for(collectible_id)
        if icon_path is None:
            return
        pixmap = QPixmap(str(icon_path))
        if pixmap.isNull():
            return
        self.detail_icon.setPixmap(pixmap.scaled(self.detail_icon.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def _clear_details(self, message: str = "Select a collectible."):
        self.current_collectible_id = None
        self.detail_icon.clear()
        self.detail_name.setText(message)
        self.detail_type.clear()
        self.detail_description.clear()
        self.detail_hint.clear()
        self.detail_flags.clear()
        self.collected.setChecked(False)
        self.acquired_on.clear()
        self.notes.clear()
        self.save_progress.setEnabled(False)

    def closeEvent(self, event):
        self.service.close()
        super().closeEvent(event)
