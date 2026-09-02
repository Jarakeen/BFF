from __future__ import annotations

"""Expose learned Recipes and Furnishing Plans inside the Collectibles workspace."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidgetItem

from services.learned_recipe_service import KIND_BY_CATEGORY, LearnedRecipeService

_INSTALLED = False
LEARNED_CATEGORIES = frozenset(KIND_BY_CATEGORY)


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui import collectibles_page

    original_init = collectibles_page.CollectiblesPage.__init__
    original_set_category = collectibles_page.CollectiblesPage.set_category
    original_refresh = collectibles_page.CollectiblesPage.refresh
    original_selection_changed = collectibles_page.CollectiblesPage._selection_changed
    original_save_detail_status = collectibles_page.CollectiblesPage._save_detail_status
    original_save_pending_changes = collectibles_page.CollectiblesPage.save_pending_changes
    original_close_event = collectibles_page.CollectiblesPage.closeEvent

    def is_learned_category(self) -> bool:
        return self.category in LEARNED_CATEGORIES

    def init_with_learned_collections(self, parent=None):
        original_init(self, parent)
        self.learned_recipe_service = LearnedRecipeService(self.data_dir / "eso.db")

    def set_category_with_learned(self, category: str):
        category = category or self.DEFAULT_CATEGORY
        if category not in LEARNED_CATEGORIES:
            self.backup_button.setVisible(True)
            self.collected.setText("Collected")
            self.acquired_on.setPlaceholderText("Acquired on (YYYY-MM-DD, optional)")
            return original_set_category(self, category)

        if self.has_pending_changes() and category != self.category:
            self.status.warning("Save or discard pending changes before changing collection categories.")
            return

        self.category = category
        self.header.title.setText(category)
        self.header.subtitle.setText(
            f"Browse ESO {category.lower()} and track what the selected profile has learned."
        )
        self.list_card.set_title(category)
        self.search.clear()
        self._last_clicked_row = None
        self._clear_details()
        self.backup_button.setVisible(False)
        self.collected.setText("Learned")
        self.acquired_on.setPlaceholderText("Learned on (YYYY-MM-DD, optional)")
        refresh_with_learned(self)

    def refresh_with_learned(self):
        if not is_learned_category(self):
            return original_refresh(self)

        service = self.learned_recipe_service
        if hasattr(self.service, "active_profile"):
            service.set_active_profile(self.service.active_profile)

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

        rows = service.items(self.category, self.search.text())
        selected_row = -1
        for index, row in enumerate(rows):
            item_id = int(row["id"])
            item = QListWidgetItem(row["name"])
            item.setData(Qt.ItemDataRole.UserRole, item_id)
            item.setData(Qt.ItemDataRole.UserRole + 1, bool(row.get("owned")))
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            effective = self.pending_changes.get(item_id, bool(row.get("owned")))
            item.setCheckState(Qt.CheckState.Checked if effective else Qt.CheckState.Unchecked)

            if self.category == "Furnishing Plans":
                result_name = (row.get("result_name") or "").strip()
                plan_type = (row.get("plan_type") or "").strip()
                meta = " · ".join(value for value in (plan_type, result_name) if value)
            else:
                quality = row.get("recipe_quality")
                rank = row.get("recipe_rank")
                parts = []
                if quality not in (None, ""):
                    parts.append(f"Quality {quality}")
                if rank not in (None, ""):
                    parts.append(f"Rank {rank}")
                meta = " · ".join(parts)
            if meta:
                item.setText(f"{row['name']}   ·   {meta}")

            self.results.addItem(item)
            if selected_id is not None and item_id == selected_id:
                selected_row = index

        self._building_results = False
        learned, total = service.progress_summary(self.category)
        self.list_card.set_badge(f"{learned:,} / {total:,} learned")
        self.status.info(
            f"{len(rows):,} shown · {learned:,}/{total:,} {self.category.lower()} learned "
            f"· {len(self.pending_changes)} pending."
        )
        self._update_pending_ui()

        if rows:
            self.results.setCurrentRow(selected_row if selected_row >= 0 else 0)
        else:
            self._clear_details("No entries matched this search.")

    def selection_changed_with_learned(self, current, previous):
        if not is_learned_category(self):
            return original_selection_changed(self, current, previous)
        if current is None:
            return
        item_id = current.data(Qt.ItemDataRole.UserRole)
        if item_id is None:
            return
        service = self.learned_recipe_service
        if hasattr(self.service, "active_profile"):
            service.set_active_profile(self.service.active_profile)
        row = service.item(int(item_id))
        if not row:
            self._clear_details("Recipe or plan details are unavailable.")
            return

        self.current_collectible_id = int(item_id)
        self.detail_icon.clear()
        self.detail_name.setText(row.get("name") or "Unnamed recipe or plan")

        if self.category == "Furnishing Plans":
            meta = [row.get("plan_type") or "Furnishing Plan"]
            if row.get("result_name"):
                meta.append(f"Creates: {row['result_name']}")
        else:
            meta = ["Provisioning Recipe"]
            if row.get("recipe_rank") not in (None, ""):
                meta.append(f"Rank {row['recipe_rank']}")
            if row.get("recipe_quality") not in (None, ""):
                meta.append(f"Quality {row['recipe_quality']}")
        self.detail_type.setText(" · ".join(meta))

        description = (row.get("description") or "").strip()
        self.detail_description.setText(description or "No recipe description is available.")
        self.detail_hint.clear()
        self.detail_flags.setText(
            f"Item ID {row['id']}"
            + (f" · Result Item ID {row['result_item_id']}" if row.get("result_item_id") else "")
        )
        effective = self.pending_changes.get(self.current_collectible_id, bool(row.get("owned")))
        self.collected.setChecked(effective)
        self.acquired_on.setText(row.get("acquired_on") or "")
        self.notes.setText(row.get("notes") or "")
        self.save_progress.setEnabled(True)

    def save_detail_status_with_learned(self):
        if not is_learned_category(self):
            return original_save_detail_status(self)
        if self.current_collectible_id is None:
            return
        service = self.learned_recipe_service
        if hasattr(self.service, "active_profile"):
            service.set_active_profile(self.service.active_profile)
        service.set_progress(
            self.current_collectible_id,
            learned=self.collected.isChecked(),
            learned_on=self.acquired_on.text(),
            notes=self.notes.text(),
        )
        self.pending_changes.pop(self.current_collectible_id, None)
        self.status.success(f"{self.category[:-1] if self.category.endswith('s') else self.category} progress saved.")
        refresh_with_learned(self)

    def save_pending_changes_with_learned(self):
        if not is_learned_category(self):
            return original_save_pending_changes(self)
        if not self.pending_changes:
            return
        service = self.learned_recipe_service
        profile = self.service.active_profile if hasattr(self.service, "active_profile") else service.active_profile
        service.set_active_profile(profile)
        count = service.set_learned_batch(profile, dict(self.pending_changes))
        self.pending_changes.clear()
        self._last_clicked_row = None
        self.status.success(
            f"Saved {count} learned-status change{'s' if count != 1 else ''} for {profile}."
        )
        refresh_with_learned(self)

    def close_event_with_learned(self, event):
        if hasattr(self, "learned_recipe_service"):
            self.learned_recipe_service.close()
        original_close_event(self, event)

    collectibles_page.CollectiblesPage.__init__ = init_with_learned_collections
    collectibles_page.CollectiblesPage.set_category = set_category_with_learned
    collectibles_page.CollectiblesPage.refresh = refresh_with_learned
    collectibles_page.CollectiblesPage._selection_changed = selection_changed_with_learned
    collectibles_page.CollectiblesPage._save_detail_status = save_detail_status_with_learned
    collectibles_page.CollectiblesPage.save_pending_changes = save_pending_changes_with_learned
    collectibles_page.CollectiblesPage.closeEvent = close_event_with_learned

    _INSTALLED = True
