from __future__ import annotations

"""Expose profile-aware learned Motifs inside the Collectibles workspace."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidgetItem

from services.learned_motif_service import LearnedMotifService
from ui.collectibles_learned_recipe_support import _strip_eso_color_markup

_INSTALLED = False
CATEGORY = "Motifs"


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
        page = "collectibles:Motifs"
        if page not in {value for _label, value in children}:
            insert_at = next(
                (index + 1 for index, (label, _value) in enumerate(children) if label == "Recipes"),
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

    def is_motif_category(self) -> bool:
        return self.category == CATEGORY

    def sync_profile(self) -> LearnedMotifService:
        service = self.learned_motif_service
        if hasattr(self.service, "active_profile"):
            service.set_active_profile(self.service.active_profile)
        return service

    def init_with_motifs(self, parent=None):
        original_init(self, parent)
        self.learned_motif_service = LearnedMotifService(self.data_dir / "eso.db")

    def set_category_with_motifs(self, category: str):
        category = category or self.DEFAULT_CATEGORY
        if category != CATEGORY:
            return original_set_category(self, category)

        if self.has_pending_changes() and category != self.category:
            self.status.warning("Save or discard pending changes before changing collection categories.")
            return

        self.category = CATEGORY
        self.header.title.setText(CATEGORY)
        self.header.subtitle.setText(
            "Browse ESO crafting motifs and track which full styles and chapters the selected profile has learned."
        )
        self.list_card.set_title(CATEGORY)
        self.search.clear()
        self._last_clicked_row = None
        self._clear_details()
        self.backup_button.setVisible(False)
        self.collected.setText("Learned")
        self.acquired_on.setPlaceholderText("Learned on (YYYY-MM-DD, optional)")
        refresh_with_motifs(self)

    def refresh_with_motifs(self):
        if not is_motif_category(self):
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
            item_id = int(row["id"])
            label = row["name"]
            if int(row.get("source_variant_count") or 1) > 1:
                label += f"   ·   {row['source_variant_count']} source variants"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, item_id)
            item.setData(Qt.ItemDataRole.UserRole + 1, bool(row.get("owned")))
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            effective = self.pending_changes.get(item_id, bool(row.get("owned")))
            item.setCheckState(Qt.CheckState.Checked if effective else Qt.CheckState.Unchecked)
            self.results.addItem(item)
            if selected_id is not None and item_id == selected_id:
                selected_row = index

        self._building_results = False
        learned, total = service.progress_summary()
        self.list_card.set_badge(f"{learned:,} / {total:,} learned")
        self.status.info(
            f"{len(rows):,} shown · {learned:,}/{total:,} motifs learned · {len(self.pending_changes)} pending."
        )
        self._update_pending_ui()
        if rows:
            self.results.setCurrentRow(selected_row if selected_row >= 0 else 0)
        else:
            self._clear_details("No motifs matched this search.")

    def selection_changed_with_motifs(self, current, previous):
        if not is_motif_category(self):
            return original_selection_changed(self, current, previous)
        if current is None:
            return
        item_id = current.data(Qt.ItemDataRole.UserRole)
        if item_id is None:
            return
        row = sync_profile(self).item(int(item_id))
        if not row:
            self._clear_details("Motif details are unavailable.")
            return

        self.current_collectible_id = int(item_id)
        self.detail_icon.clear()
        self.detail_name.setText(row.get("name") or "Unnamed motif")
        detail_kind = "Full Style Book" if row.get("is_full_style") else f"{row.get('part_name') or 'Chapter'} Chapter"
        self.detail_type.setText(
            f"Motif {row['motif_number']} · {row['style_name']} · {detail_kind}"
        )
        description = _strip_eso_color_markup((row.get("description") or "").strip())
        self.detail_description.setText(description or "No motif description is available.")
        self.detail_hint.clear()
        variants = int(row.get("source_variant_count") or 1)
        self.detail_flags.setText(
            f"Item ID {row['id']}"
            + (f" · {variants} source item variants collapsed" if variants > 1 else "")
        )
        effective = self.pending_changes.get(self.current_collectible_id, bool(row.get("owned")))
        self.collected.setChecked(effective)
        self.acquired_on.setText(row.get("acquired_on") or "")
        self.notes.setText(row.get("notes") or "")
        self.save_progress.setEnabled(True)

    def save_detail_status_with_motifs(self):
        if not is_motif_category(self):
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
        self.status.success("Motif progress saved.")
        refresh_with_motifs(self)

    def save_pending_changes_with_motifs(self):
        if not is_motif_category(self):
            return original_save_pending_changes(self)
        if not self.pending_changes:
            return
        service = sync_profile(self)
        profile = service.active_profile
        count = service.set_learned_batch(dict(self.pending_changes))
        self.pending_changes.clear()
        self._last_clicked_row = None
        self.status.success(
            f"Saved {count} motif learned-status change{'s' if count != 1 else ''} for {profile}."
        )
        refresh_with_motifs(self)

    def close_event_with_motifs(self, event):
        if hasattr(self, "learned_motif_service"):
            self.learned_motif_service.close()
        original_close_event(self, event)

    collectibles_page.CollectiblesPage.__init__ = init_with_motifs
    collectibles_page.CollectiblesPage.set_category = set_category_with_motifs
    collectibles_page.CollectiblesPage.refresh = refresh_with_motifs
    collectibles_page.CollectiblesPage._selection_changed = selection_changed_with_motifs
    collectibles_page.CollectiblesPage._save_detail_status = save_detail_status_with_motifs
    collectibles_page.CollectiblesPage.save_pending_changes = save_pending_changes_with_motifs
    collectibles_page.CollectiblesPage.closeEvent = close_event_with_motifs

    _INSTALLED = True
