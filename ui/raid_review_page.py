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

from engine.config import DEFAULT_DATABASE
from services.encounter_boss_guide import EncounterBossGuideService
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


def _display_clock(value: object) -> str:
    text = _clean(value)
    if not text:
        return ""
    try:
        return datetime.fromisoformat(text).astimezone().strftime("%I:%M %p").lstrip("0")
    except ValueError:
        return ""


def _display_duration(value: object) -> str:
    try:
        seconds = max(0, int(value))
    except (TypeError, ValueError):
        return ""
    minutes, second = divmod(seconds, 60)
    hours, minute = divmod(minutes, 60)
    if hours:
        return f"{hours:d}:{minute:02d}:{second:02d}"
    return f"{minute:02d}:{second:02d}"


def _display_timestamp(value: object) -> str:
    text = _clean(value)
    if not text:
        return "Unknown time"
    try:
        return datetime.fromisoformat(text).astimezone().strftime("%Y-%m-%d %I:%M %p")
    except ValueError:
        return text


class RaidReviewPage(FoundryPage):
    """Index manual Live Raid attempts and optional notes by date, trial, and encounter."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.state = RaidSectionStateService()
        self.guide_service = EncounterBossGuideService(DEFAULT_DATABASE)
        self._rows_by_id: dict[str, dict] = {}
        self._encounter_labels: dict[str, str] = {}
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        self.header = FoundryHeader(
            title="Review",
            subtitle="Attempts and run notes, organized after the shouting stops.",
            department="RAID • REVIEW",
            icon="archive",
        )
        self.set_header(self.header)

        split = QSplitter(Qt.Orientation.Horizontal)
        split.setChildrenCollapsible(False)

        index_card = FoundryCard("Attempts", "archive")
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
        self.note_body.setPlaceholderText("Saved Live Raid notes will appear here when present.")
        note_card.addWidget(self.note_body)
        split.addWidget(note_card)

        split.setStretchFactor(0, 2)
        split.setStretchFactor(1, 5)
        self.workspace_layout.addWidget(split, 1)

    def _encounter_label(self, encounter_id: str) -> str:
        key = _clean(encounter_id)
        if not key:
            return "Trial / General"
        if key in self._encounter_labels:
            return self._encounter_labels[key]
        try:
            label = _clean(self.guide_service.get(key).name) or key
        except Exception:
            label = key.replace("_", " ").replace("-", " ").title()
        self._encounter_labels[key] = label
        return label

    def refresh(self) -> None:
        attempts = self.state.all_attempt_history()
        notes = self.state.review_notes()
        notes_by_attempt = {
            (_clean(row.get("plan_id")), int(row.get("attempt", 0) or 0)): row
            for row in notes
            if int(row.get("attempt", 0) or 0) > 0
        }
        general_notes = [
            row for row in notes
            if int(row.get("attempt", 0) or 0) <= 0
        ]

        rows: list[dict] = []
        for attempt in attempts:
            note = notes_by_attempt.get((attempt.plan_id, attempt.attempt))
            row = {
                "review_id": f"attempt:{attempt.plan_id}:{attempt.attempt}",
                "plan_id": attempt.plan_id,
                "trial_id": attempt.trial_id,
                "plan_name": attempt.plan_name,
                "attempt": attempt.attempt,
                "encounter_id": attempt.encounter_id,
                "started_at": attempt.started_at,
                "ended_at": attempt.ended_at,
                "duration_seconds": attempt.duration_seconds,
                "notes": _clean(note.get("notes")) if note else "",
                "updated_at": _clean(note.get("updated_at")) if note else "",
                "created_at": _clean(note.get("created_at")) if note else "",
            }
            rows.append(row)

        for row in general_notes:
            copied = dict(row)
            copied["review_id"] = _clean(row.get("review_id")) or (
                f"general:{_clean(row.get('plan_id'))}:{_clean(row.get('created_at'))}"
            )
            rows.append(copied)

        rows.sort(
            key=lambda row: _clean(
                row.get("started_at")
                or row.get("updated_at")
                or row.get("created_at")
            ),
            reverse=True,
        )

        self._rows_by_id = {
            _clean(row.get("review_id")): row
            for row in rows
            if _clean(row.get("review_id"))
        }
        self.index.clear()
        groups: dict[str, dict[str, QTreeWidgetItem]] = {}

        for row in rows:
            date_label = _display_date(
                row.get("started_at")
                or row.get("updated_at")
                or row.get("created_at")
            )
            trial = _clean(row.get("trial_id")) or "Unknown Trial"
            encounter = self._encounter_label(_clean(row.get("encounter_id")))
            date_item = groups.setdefault(date_label, {}).get("__date__")
            if date_item is None:
                date_item = QTreeWidgetItem([date_label])
                date_item.setData(0, Qt.ItemDataRole.UserRole, "")
                self.index.addTopLevelItem(date_item)
                groups[date_label]["__date__"] = date_item

            trial_key = f"trial:{trial}"
            trial_item = groups[date_label].get(trial_key)
            if trial_item is None:
                trial_item = QTreeWidgetItem([trial])
                trial_item.setData(0, Qt.ItemDataRole.UserRole, "")
                date_item.addChild(trial_item)
                groups[date_label][trial_key] = trial_item

            encounter_key = f"encounter:{trial}:{encounter}"
            encounter_item = groups[date_label].get(encounter_key)
            if encounter_item is None:
                encounter_item = QTreeWidgetItem([encounter])
                encounter_item.setData(0, Qt.ItemDataRole.UserRole, "")
                trial_item.addChild(encounter_item)
                groups[date_label][encounter_key] = encounter_item

            attempt = int(row.get("attempt", 0) or 0)
            label = f"Attempt #{attempt}" if attempt else "General note"
            started_clock = _display_clock(row.get("started_at"))
            duration = _display_duration(row.get("duration_seconds"))
            if started_clock:
                label += f" · {started_clock}"
            if duration:
                label += f" · {duration}"
            if _clean(row.get("notes")):
                label += " · NOTE"
            plan_name = _clean(row.get("plan_name"))
            if plan_name:
                label += f" · {plan_name}"
            item = QTreeWidgetItem([label])
            item.setData(0, Qt.ItemDataRole.UserRole, _clean(row.get("review_id")))
            encounter_item.addChild(item)

        self.index.expandAll()
        if rows:
            first_date = self.index.topLevelItem(0)
            first_trial = first_date.child(0) if first_date is not None else None
            first_encounter = first_trial.child(0) if first_trial is not None else None
            first_item = first_encounter.child(0) if first_encounter is not None else None
            if first_item is not None:
                self.index.setCurrentItem(first_item)
        else:
            self.note_heading.setText("No attempts yet")
            self.note_meta.setText("Start a pull from Raid Plan → Run to build this journal.")
            self.note_body.clear()

    def _show_selected_note(self, item: QTreeWidgetItem | None, _previous=None) -> None:
        review_id = _clean(item.data(0, Qt.ItemDataRole.UserRole)) if item is not None else ""
        row = self._rows_by_id.get(review_id)
        if row is None:
            return

        attempt = int(row.get("attempt", 0) or 0)
        trial = _clean(row.get("trial_id")) or "Unknown Trial"
        plan = _clean(row.get("plan_name")) or "Unnamed Raid Plan"
        encounter = self._encounter_label(_clean(row.get("encounter_id")))
        self.note_heading.setText(f"{trial} · {encounter} · {plan}")
        meta = [
            f"Saved {_display_timestamp(row.get('updated_at') or row.get('created_at'))}",
            f"Attempt #{attempt}" if attempt else "General note",
        ]
        started = _clean(row.get("started_at"))
        ended = _clean(row.get("ended_at"))
        duration = _display_duration(row.get("duration_seconds"))
        if started:
            meta.append(f"Started {_display_timestamp(started)}")
        if ended:
            meta.append(f"Ended {_display_timestamp(ended)}")
        if duration:
            meta.append(f"Duration {duration}")
        has_note = bool(_clean(row.get("notes")))
        meta.append("Saved note" if has_note else "No saved note")
        self.note_meta.setText(" · ".join(meta))
        self.note_body.setPlainText(
            _clean(row.get("notes"))
            if has_note
            else "No run note was saved for this attempt."
        )


__all__ = ["RaidReviewPage"]
