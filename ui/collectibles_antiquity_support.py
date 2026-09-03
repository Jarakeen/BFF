from __future__ import annotations

"""Expose profile-aware Antiquities inside the Collectibles workspace."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidgetItem

from services.antiquity_service import AntiquityService

_INSTALLED = False
CATEGORY = "Antiquities"


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui import collectibles_page
    from ui.components import foundry_sidebar

    # Antiquities are their own collection type. They are not ESO Collectibles
    # records, so keep them out of the canonical collectible table while still
    # presenting them in the Collections workspace.
    for section in foundry_sidebar.CORE_NAV_SECTIONS:
        if not isinstance(section, dict) or section.get("label") != "Collections":
            continue
        children = section["children"]
        route = "collectibles:Antiquities"
        if route not in {value for _label, value in children}:
            # Put archaeology/reference collection types together when Motifs
            # and Lorebooks have already registered themselves.
            insert_at = next(
                (
                    index + 1
                    for index, (label, _value) in enumerate(children)
                    if label in {"Lorebooks", "Motifs"}
                ),
                len(children),
            )
            children.insert(insert_at, (CATEGORY, route))
        break

    original_init = collectibles_page.CollectiblesPage.__init__
    original_set_category = collectibles_page.CollectiblesPage.set_category
    original_refresh = collectibles_page.CollectiblesPage.refresh
    original_selection_changed = collectibles_page.CollectiblesPage._selection_changed
    original_save_detail_status = collectibles_page.CollectiblesPage._save_detail_status
    original_save_pending_changes = collectibles_page.CollectiblesPage.save_pending_changes
    original_close_event = collectibles_page.CollectiblesPage.closeEvent

    def is_antiquity_category(self) -> bool:
        return self.category == CATEGORY

    def sync_profile(self) -> AntiquityService:
        service = self.antiquity_service
        if hasattr(self.service, "active_profile"):
            service.set_active_profile(self.service.active_profile)
        return service

    def init_with_antiquities(self, parent=None):
        original_init(self, parent)
        self.antiquity_service = AntiquityService(self.data_dir)

    def set_category_with_antiquities(self, category: str):
        category = category or self.DEFAULT_CATEGORY
        if category != CATEGORY:
            return original_set_category(self, category)

        if self.has_pending_changes() and category != self.category:
            self.status.warning("Save or discard pending changes before changing collection categories.")
            return

        self.category = CATEGORY
        self.header.title.setText(CATEGORY)
        self.header.subtitle.setText(
            "Track ESO Antiquities recovered by the selected profile, including leads, zones, and multi-part rewards."
        )
        self.list_card.set_title(CATEGORY)
        self.search.clear()
        self.search.setPlaceholderText("Search antiquities by name, zone, or reward set...")
        self._last_clicked_row = None
        self._clear_details()
        self.backup_button.setVisible(False)
        self.collected.setText("Recovered")
        self.acquired_on.setPlaceholderText("Recovered on (YYYY-MM-DD, optional)")
        refresh_with_antiquities(self)

    def refresh_with_antiquities(self):
        if not is_antiquity_category(self):
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
            antiquity_id = int(row["id"])
            label = row["name"]
            zone = (row.get("category_name") or "").strip()
            reward_set = (row.get("set_name") or "").strip()
            meta = " · ".join(value for value in (zone, reward_set) if value)
            if meta:
                label = f"{label}   ·   {meta}"

            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, antiquity_id)
            item.setData(Qt.ItemDataRole.UserRole + 1, bool(row.get("owned")))
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            effective = self.pending_changes.get(antiquity_id, bool(row.get("owned")))
            item.setCheckState(Qt.CheckState.Checked if effective else Qt.CheckState.Unchecked)
            self.results.addItem(item)
            if selected_id is not None and antiquity_id == selected_id:
                selected_row = index

        self._building_results = False
        recovered, total = service.progress_summary()
        self.list_card.set_badge(f"{recovered:,} / {total:,} recovered")
        self.status.info(
            f"{len(rows):,} shown · {recovered:,}/{total:,} antiquities recovered "
            f"· {len(self.pending_changes)} pending."
        )
        self._update_pending_ui()

        if rows:
            self.results.setCurrentRow(selected_row if selected_row >= 0 else 0)
        else:
            self._clear_details("No antiquities matched this search.")

    def selection_changed_with_antiquities(self, current, previous):
        if not is_antiquity_category(self):
            return original_selection_changed(self, current, previous)
        if current is None:
            return
        antiquity_id = current.data(Qt.ItemDataRole.UserRole)
        if antiquity_id is None:
            return
        row = sync_profile(self).item(int(antiquity_id))
        if not row:
            self._clear_details("Antiquity details are unavailable.")
            return

        self.current_collectible_id = int(antiquity_id)
        self.detail_icon.clear()
        self.detail_name.setText(row.get("name") or "Unnamed antiquity")

        zone = (row.get("category_name") or "Unknown zone").strip()
        quality = int(row.get("quality", -1))
        difficulty = int(row.get("difficulty", -1))
        self.detail_type.setText(
            f"{zone} · Quality {quality} · Difficulty {difficulty}"
        )

        reward_set = (row.get("set_name") or "").strip()
        if reward_set:
            set_count = int(row.get("set_count", -1))
            description = f"Part of: {reward_set}"
            if set_count > 0:
                description += f" · {set_count} leads in set"
            self.detail_description.setText(description)
        else:
            reward_id = int(row.get("reward_id") or 0)
            self.detail_description.setText(
                f"Reward ID {reward_id}" if reward_id > 0 else "No grouped reward is recorded for this antiquity."
            )

        lead_text = "Lead required" if row.get("requires_lead") else "No lead required"
        repeat_text = "Repeatable" if row.get("repeatable") else "Not repeatable"
        self.detail_hint.setText(f"{lead_text} · {repeat_text}")
        self.detail_flags.setText(
            f"UESP Antiquity ID {row['id']} · Zone ID {row.get('zone_id', 0)}"
        )

        effective = self.pending_changes.get(self.current_collectible_id, bool(row.get("owned")))
        self.collected.setChecked(effective)
        self.acquired_on.setText(row.get("acquired_on") or "")
        self.notes.setText(row.get("notes") or "")
        self.save_progress.setEnabled(True)

    def save_detail_status_with_antiquities(self):
        if not is_antiquity_category(self):
            return original_save_detail_status(self)
        if self.current_collectible_id is None:
            return
        service = sync_profile(self)
        service.set_progress(
            self.current_collectible_id,
            recovered=self.collected.isChecked(),
            recovered_on=self.acquired_on.text(),
            notes=self.notes.text(),
        )
        self.pending_changes.pop(self.current_collectible_id, None)
        self.status.success("Antiquity progress saved.")
        refresh_with_antiquities(self)

    def save_pending_changes_with_antiquities(self):
        if not is_antiquity_category(self):
            return original_save_pending_changes(self)
        if not self.pending_changes:
            return
        service = sync_profile(self)
        profile = service.active_profile
        count = service.set_recovered_batch(dict(self.pending_changes))
        self.pending_changes.clear()
        self._last_clicked_row = None
        self.status.success(
            f"Saved {count} antiquity progress change{'s' if count != 1 else ''} for {profile}."
        )
        refresh_with_antiquities(self)

    def close_event_with_antiquities(self, event):
        if hasattr(self, "antiquity_service"):
            self.antiquity_service.close()
        original_close_event(self, event)

    collectibles_page.CollectiblesPage.__init__ = init_with_antiquities
    collectibles_page.CollectiblesPage.set_category = set_category_with_antiquities
    collectibles_page.CollectiblesPage.refresh = refresh_with_antiquities
    collectibles_page.CollectiblesPage._selection_changed = selection_changed_with_antiquities
    collectibles_page.CollectiblesPage._save_detail_status = save_detail_status_with_antiquities
    collectibles_page.CollectiblesPage.save_pending_changes = save_pending_changes_with_antiquities
    collectibles_page.CollectiblesPage.closeEvent = close_event_with_antiquities

    _INSTALLED = True
