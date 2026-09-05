from __future__ import annotations

"""Expose profile-aware Lorebooks inside the Collectibles workspace."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidgetItem, QPlainTextEdit, QSizePolicy

from services.lorebook_service import LorebookService

_INSTALLED = False
CATEGORY = "Lorebooks"


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui import collectibles_page
    from ui.components import foundry_sidebar

    for section in foundry_sidebar.CORE_NAV_SECTIONS:
        if not isinstance(section, dict) or section.get("label") != "Collections":
            continue
        children = section["children"]
        page = "collectibles:Lorebooks"
        if page not in {value for _label, value in children}:
            insert_at = next(
                (index + 1 for index, (label, _value) in enumerate(children) if label == "Motifs"),
                len(children),
            )
            children.insert(insert_at, (CATEGORY, page))
        break

    original_init = collectibles_page.CollectiblesPage.__init__
    original_set_category = collectibles_page.CollectiblesPage.set_category
    original_refresh = collectibles_page.CollectiblesPage.refresh
    original_selection_changed = collectibles_page.CollectiblesPage._selection_changed
    original_save_detail_status = collectibles_page.CollectiblesPage._save_detail_status
    original_save_pending_changes = collectibles_page.CollectiblesPage.save_pending_changes
    original_close_event = collectibles_page.CollectiblesPage.closeEvent

    def is_lorebook_category(self) -> bool:
        return self.category == CATEGORY

    def sync_profile(self) -> LorebookService:
        service = self.lorebook_service
        if hasattr(self.service, "active_profile"):
            service.set_active_profile(self.service.active_profile)
        return service

    def init_with_lorebooks(self, parent=None):
        original_init(self, parent)
        self.lorebook_service = LorebookService(self.data_dir / "eso.db")
        self.lorebook_text = QPlainTextEdit()
        self.lorebook_text.setReadOnly(True)
        self.lorebook_text.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.lorebook_text.setPlaceholderText("Select a lorebook to read it here.")
        self.lorebook_text.setMinimumHeight(280)
        self.lorebook_text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.lorebook_text.setVisible(False)
        detail_index = self.detail_card.body_layout.indexOf(self.detail_description)
        self.detail_card.body_layout.insertWidget(max(0, detail_index), self.lorebook_text, 1)

    def set_category_with_lorebooks(self, category: str):
        category = category or self.DEFAULT_CATEGORY
        if category != CATEGORY:
            if hasattr(self, "lorebook_text"):
                self.lorebook_text.clear()
                self.lorebook_text.setVisible(False)
            self.detail_description.setVisible(True)
            return original_set_category(self, category)

        if self.has_pending_changes() and category != self.category:
            self.status.warning("Save or discard pending changes before changing collection categories.")
            return

        self.category = CATEGORY
        self.header.title.setText(CATEGORY)
        self.header.subtitle.setText(
            "Browse ESO lorebooks, track which ones the selected profile has found, and read the full text."
        )
        self.list_card.set_title(CATEGORY)
        self.search.clear()
        self.search.setPlaceholderText("Search lorebook titles, full text, or associated skill...")
        self._last_clicked_row = None
        self._clear_details()
        self.backup_button.setVisible(False)
        self.collected.setText("Found")
        self.acquired_on.setPlaceholderText("Found on (YYYY-MM-DD, optional)")
        self.detail_description.setVisible(False)
        self.lorebook_text.setVisible(True)
        refresh_with_lorebooks(self)

    def refresh_with_lorebooks(self):
        if not is_lorebook_category(self):
            return original_refresh(self)

        service = sync_profile(self)
        selected_id = self.current_collectible_id
        self._building_results = True
        self.results.clear()

        if not service.available:
            item = QListWidgetItem(service.bootstrap_message)
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.results.addItem(item)
            self.list_card.set_badge("0")
            self._building_results = False
            self.status.warning(service.bootstrap_message)
            return

        rows = service.items(self.search.text())
        selected_row = -1
        for index, row in enumerate(rows):
            lorebook_id = int(row["id"])
            label = row["name"]
            occurrences = int(row.get("source_occurrence_count") or 1)
            if occurrences > 1:
                label += f"   ·   {occurrences} source occurrences"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, lorebook_id)
            item.setData(Qt.ItemDataRole.UserRole + 1, bool(row.get("owned")))
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            effective = self.pending_changes.get(lorebook_id, bool(row.get("owned")))
            item.setCheckState(Qt.CheckState.Checked if effective else Qt.CheckState.Unchecked)
            self.results.addItem(item)
            if selected_id is not None and lorebook_id == selected_id:
                selected_row = index

        self._building_results = False
        found, total = service.progress_summary()
        self.list_card.set_badge(f"{found:,} / {total:,} found")
        self.status.info(
            f"{len(rows):,} shown · {found:,}/{total:,} lorebooks found · {len(self.pending_changes)} pending."
        )
        self._update_pending_ui()
        if rows:
            self.results.setCurrentRow(selected_row if selected_row >= 0 else 0)
        else:
            self._clear_details("No lorebooks matched this search.")
            self.lorebook_text.clear()

    def selection_changed_with_lorebooks(self, current, previous):
        if not is_lorebook_category(self):
            return original_selection_changed(self, current, previous)
        if current is None:
            return
        lorebook_id = current.data(Qt.ItemDataRole.UserRole)
        if lorebook_id is None:
            return
        row = sync_profile(self).item(int(lorebook_id))
        if not row:
            self._clear_details("Lorebook details are unavailable.")
            self.lorebook_text.clear()
            return

        self.current_collectible_id = int(lorebook_id)
        self.detail_icon.clear()
        self.detail_name.setText(row.get("name") or "Untitled lorebook")
        meta = ["Lorebook"]
        if row.get("skill"):
            meta.append(str(row["skill"]))
        self.detail_type.setText(" · ".join(meta))
        self.detail_description.clear()
        self.detail_description.setVisible(False)
        self.lorebook_text.setVisible(True)
        self.lorebook_text.setPlainText((row.get("body") or "").strip() or "No book text is available.")
        self.lorebook_text.moveCursor(self.lorebook_text.textCursor().MoveOperation.Start)
        self.detail_hint.clear()
        flags = []
        if row.get("primary_book_id") is not None:
            flags.append(f"Book ID {row['primary_book_id']}")
        occurrences = int(row.get("source_occurrence_count") or 1)
        if occurrences > 1:
            flags.append(f"{occurrences} source occurrences collapsed")
        self.detail_flags.setText(" · ".join(flags))
        effective = self.pending_changes.get(self.current_collectible_id, bool(row.get("owned")))
        self.collected.setChecked(effective)
        self.acquired_on.setText(row.get("acquired_on") or "")
        self.notes.setText(row.get("notes") or "")
        self.save_progress.setEnabled(True)

    def save_detail_status_with_lorebooks(self):
        if not is_lorebook_category(self):
            return original_save_detail_status(self)
        if self.current_collectible_id is None:
            return
        service = sync_profile(self)
        service.set_progress(
            self.current_collectible_id,
            learned=self.collected.isChecked(),
            learned_on=self.acquired_on.text(),
            notes=self.notes.text(),
        )
        self.pending_changes.pop(self.current_collectible_id, None)
        self.status.success("Lorebook progress saved.")
        refresh_with_lorebooks(self)

    def save_pending_changes_with_lorebooks(self):
        if not is_lorebook_category(self):
            return original_save_pending_changes(self)
        if not self.pending_changes:
            return
        service = sync_profile(self)
        count = service.set_learned_batch(dict(self.pending_changes))
        self.pending_changes.clear()
        self._last_clicked_row = None
        self.status.success(
            f"Saved {count} lorebook found-status change{'s' if count != 1 else ''} for {service.active_profile}."
        )
        refresh_with_lorebooks(self)

    def close_event_with_lorebooks(self, event):
        if hasattr(self, "lorebook_service"):
            self.lorebook_service.close()
        original_close_event(self, event)

    collectibles_page.CollectiblesPage.__init__ = init_with_lorebooks
    collectibles_page.CollectiblesPage.set_category = set_category_with_lorebooks
    collectibles_page.CollectiblesPage.refresh = refresh_with_lorebooks
    collectibles_page.CollectiblesPage._selection_changed = selection_changed_with_lorebooks
    collectibles_page.CollectiblesPage._save_detail_status = save_detail_status_with_lorebooks
    collectibles_page.CollectiblesPage.save_pending_changes = save_pending_changes_with_lorebooks
    collectibles_page.CollectiblesPage.closeEvent = close_event_with_lorebooks

    # The dashboard is built later by MainWindow. Install its recovered-data
    # ledgers now so Recipes, Furnishing Plans, and Lorebooks appear alongside
    # the canonical collectible categories as soon as the app starts.
    from ui.collectibles_reference_dashboard_support import install as install_reference_dashboard_support
    install_reference_dashboard_support()

    _INSTALLED = True
