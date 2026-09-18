from __future__ import annotations

"""Manual Raid Review journal built from Live Raid run notes."""

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSplitter,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from services.raid_section_state_service import RaidSectionStateService
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_header import FoundryHeader
from ui.foundry_page import FoundryPage


def _clean(value: object) -> str:
    return str(value or "").strip()


def _display_date(value: object) -> str:
    text = _clean(value)
    if not text:
        return "Unknown date"
    try:
        return datetime.fromisoformat(text).astimezone().strftime("%Y-%m-%d")
    except ValueError:
        return text[:10] or "Unknown date"


def _display_timestamp(value: object) -> str:
    text = _clean(value)
    if not text:
        return "Unknown time"
    try:
        return datetime.fromisoformat(text).astimezone().strftime("%Y-%m-%d %I:%M %p")
    except ValueError:
        return text


class RaidReviewPage(FoundryPage):
    """Index manual Live Raid notes by date and trial."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.state = RaidSectionStateService()
        self._notes_by_id: dict[str, dict] = {}
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        self.header = FoundryHeader(
            title="Review",
            subtitle="Run notes, organized after the shouting stops.",
            department="RAID • REVIEW",
            icon="archive",
        )
        self.set_header(self.header)

        split = QSplitter(Qt.Orientation.Horizontal)
        split.setChildrenCollapsible(False)

        index_card = FoundryCard("Run Notes", "archive")
        self.index = QTreeWidget()
        self.index.setHeaderHidden(True)
        self.index.setMinimumWidth(300)
        self.index.currentItemChanged.connect(self._show_selected_note)
        index_card.addWidget(self.index)
        split.addWidget(index_card)

        note_card = FoundryCard("Review Note", "clipboard")
        self.note_heading = QLabel("Select a run note")
        self.note_heading.setProperty("heroTitle", True)
        self.note_heading.setWordWrap(True)
        note_card.addWidget(self.note_heading)

        self.note_meta = QLabel("")
        self.note_meta.setProperty("muted", True)
        self.note_meta.setWordWrap(True)
        note_card.addWidget(self.note_meta)

        self.note_body = QTextEdit()
        self.note_body.setReadOnly(True)
        self.note_body.setPlaceholderText("Saved Live Raid notes will appear here.")
        note_card.addWidget(self.note_body)
        split.addWidget(note_card)

        split.setStretchFactor(0, 2)
        split.setStretchFactor(1, 5)
        self.workspace_layout.addWidget(split, 1)

    def refresh(self) -> None:
        rows = self.state.review_notes()
        self._notes_by_id = {
            _clean(row.get("review_id")): row
            for row in rows
            if _clean(row.get("review_id"))
        }
        self.index.clear()
        groups: dict[str, dict[str, QTreeWidgetItem]] = {}

        for row in rows:
            date_label = _display_date(row.get("updated_at") or row.get("created_at"))
            trial = _clean(row.get("trial_id")) or "Unknown Trial"
            date_item = groups.setdefault(date_label, {}).get("__date__")
            if date_item is None:
                date_item = QTreeWidgetItem([date_label])
                date_item.setData(0, Qt.ItemDataRole.UserRole, "")
                self.index.addTopLevelItem(date_item)
                groups[date_label]["__date__"] = date_item

            trial_item = groups[date_label].get(trial)
            if trial_item is None:
                trial_item = QTreeWidgetItem([trial])
                trial_item.setData(0, Qt.ItemDataRole.UserRole, "")
                date_item.addChild(trial_item)
                groups[date_label][trial] = trial_item

            attempt = int(row.get("attempt", 0) or 0)
            label = f"Attempt #{attempt}" if attempt else "General note"
            plan_name = _clean(row.get("plan_name"))
            if plan_name:
                label += f" · {plan_name}"
            note_item = QTreeWidgetItem([label])
            note_item.setData(0, Qt.ItemDataRole.UserRole, _clean(row.get("review_id")))
            trial_item.addChild(note_item)

        self.index.expandAll()
        if rows:
            first_date = self.index.topLevelItem(0)
            first_trial = first_date.child(0) if first_date is not None else None
            first_note = first_trial.child(0) if first_trial is not None else None
            if first_note is not None:
                self.index.setCurrentItem(first_note)
        else:
            self.note_heading.setText("No review notes yet")
            self.note_meta.setText("Save notes from Raid Plan → Run to build this journal.")
            self.note_body.clear()

    def _show_selected_note(self, item: QTreeWidgetItem | None, _previous=None) -> None:
        review_id = _clean(item.data(0, Qt.ItemDataRole.UserRole)) if item is not None else ""
        row = self._notes_by_id.get(review_id)
        if row is None:
            return

        attempt = int(row.get("attempt", 0) or 0)
        trial = _clean(row.get("trial_id")) or "Unknown Trial"
        plan = _clean(row.get("plan_name")) or "Unnamed Raid Plan"
        self.note_heading.setText(f"{trial} · {plan}")
        self.note_meta.setText(
            f"{_display_timestamp(row.get('updated_at') or row.get('created_at'))}"
            + (f" · Attempt #{attempt}" if attempt else " · General note")
        )
        self.note_body.setPlainText(_clean(row.get("notes")))


__all__ = ["RaidReviewPage"]
