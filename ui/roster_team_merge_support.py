from __future__ import annotations

"""Explicitly merge one roster team into another without deleting player/build identity.

This is a UI workflow over the existing roster/team SQLite state and canonical
Player -> Character -> Build catalog. The destination team survives. Source
memberships and build assignments move to it, duplicate memberships/assignments
collapse, destination schedule/focus values win conflicts, and only the source
team record is retired.
"""

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from engine.config import get_data_dir
from services.build_service import BuildService
from services.user_safety_snapshot_service import UserSafetySnapshotService
from ui.ui_safety import confirm_destructive_action


_INSTALLED = False


@dataclass(frozen=True)
class TeamMergePreview:
    source_team: str
    destination_team: str
    source_memberships: int
    duplicate_memberships: int
    source_build_assignments: int
    duplicate_build_assignments: int
    conflicts: tuple[str, ...] = ()

    @property
    def memberships_to_move(self) -> int:
        return max(0, self.source_memberships - self.duplicate_memberships)

    @property
    def build_assignments_to_move(self) -> int:
        return max(0, self.source_build_assignments - self.duplicate_build_assignments)


@dataclass(frozen=True)
class TeamMergeResult:
    source_team: str
    destination_team: str
    moved_memberships: int
    collapsed_memberships: int
    moved_build_assignments: int
    collapsed_build_assignments: int
    conflicts: tuple[str, ...] = ()


def _text(value: Any) -> str:
    return str(value or "").strip()


def _team_row(roster_service, team_name: str):
    return roster_service.db.execute(
        """
        SELECT id, name, raid_days, raid_time, timezone, raid_schedule_json, current_focus
        FROM team
        WHERE name = ? COLLATE NOCASE
        """,
        (_text(team_name),),
    ).fetchone()


def _membership_ids(roster_service, team_id: int) -> set[int]:
    rows = roster_service.db.execute(
        "SELECT roster_member_id FROM team_member WHERE team_id = ?",
        (int(team_id),),
    ).fetchall()
    return {int(row["roster_member_id"]) for row in rows}


def _schedule_conflicts(roster_service, source_team: str, destination_team: str) -> list[str]:
    source = roster_service.get_team_schedule(source_team)
    destination = roster_service.get_team_schedule(destination_team)
    if source is None or destination is None:
        return []

    conflicts: list[str] = []
    source_slots = tuple(
        (slot.Day.casefold(), slot.StartTime.casefold(), slot.EndTime.casefold())
        for slot in source.effective_slots
    )
    destination_slots = tuple(
        (slot.Day.casefold(), slot.StartTime.casefold(), slot.EndTime.casefold())
        for slot in destination.effective_slots
    )
    if source_slots and destination_slots and source_slots != destination_slots:
        conflicts.append(
            "Raid schedule differs; the destination team's existing raid schedule will be kept."
        )
    if (
        source.TimeZone.strip()
        and destination.TimeZone.strip()
        and source.TimeZone.strip().casefold() != destination.TimeZone.strip().casefold()
    ):
        conflicts.append(
            "Time zone differs; the destination team's existing time zone will be kept."
        )
    if (
        source.CurrentFocus.strip()
        and destination.CurrentFocus.strip()
        and source.CurrentFocus.strip().casefold() != destination.CurrentFocus.strip().casefold()
    ):
        conflicts.append(
            "Current focus differs; the destination team's existing focus will be kept."
        )
    return conflicts


def _assignment_conflicts(catalog: dict[str, Any], source_team: str, destination_team: str) -> list[str]:
    source_key = source_team.casefold()
    destination_key = destination_team.casefold()
    destination_by_build = {
        _text(row.get("build_id")): row
        for row in catalog.get("team_assignments", [])
        if isinstance(row, dict)
        and _text(row.get("team_name")).casefold() == destination_key
        and _text(row.get("build_id"))
    }
    conflicts: list[str] = []
    labels = {
        "raid_role": "raid role",
        "slot_name": "slot/assignment",
        "status": "assignment status",
    }
    for source in catalog.get("team_assignments", []):
        if not isinstance(source, dict):
            continue
        if _text(source.get("team_name")).casefold() != source_key:
            continue
        build_id = _text(source.get("build_id"))
        destination = destination_by_build.get(build_id)
        if destination is None:
            continue
        for field, label in labels.items():
            left = _text(source.get(field))
            right = _text(destination.get(field))
            if left and right and left.casefold() != right.casefold():
                conflicts.append(
                    f"Build {build_id[:8] or 'unknown'} has different {label}; "
                    "the destination assignment will be kept."
                )
    return conflicts


def preview_team_merge(
    roster_service,
    build_service: BuildService,
    source_team: str,
    destination_team: str,
) -> TeamMergePreview:
    source_name = _text(source_team)
    destination_name = _text(destination_team)
    if not source_name or not destination_name:
        raise ValueError("Choose both a source team and a destination team.")
    if source_name.casefold() == destination_name.casefold():
        raise ValueError("Source and destination must be different teams.")

    source_row = _team_row(roster_service, source_name)
    destination_row = _team_row(roster_service, destination_name)
    if source_row is None:
        raise ValueError(f"Source team does not exist: {source_name}")
    if destination_row is None:
        raise ValueError(f"Destination team does not exist: {destination_name}")

    source_members = _membership_ids(roster_service, int(source_row["id"]))
    destination_members = _membership_ids(roster_service, int(destination_row["id"]))

    catalog = build_service.canonical.catalog_service.load()
    source_key = source_name.casefold()
    destination_key = destination_name.casefold()
    source_assignments = [
        row
        for row in catalog.get("team_assignments", [])
        if isinstance(row, dict) and _text(row.get("team_name")).casefold() == source_key
    ]
    destination_build_ids = {
        _text(row.get("build_id"))
        for row in catalog.get("team_assignments", [])
        if isinstance(row, dict)
        and _text(row.get("team_name")).casefold() == destination_key
        and _text(row.get("build_id"))
    }
    duplicate_assignments = sum(
        1 for row in source_assignments if _text(row.get("build_id")) in destination_build_ids
    )

    conflicts = _schedule_conflicts(roster_service, source_name, destination_name)
    conflicts.extend(_assignment_conflicts(catalog, source_name, destination_name))

    return TeamMergePreview(
        source_team=str(source_row["name"]),
        destination_team=str(destination_row["name"]),
        source_memberships=len(source_members),
        duplicate_memberships=len(source_members & destination_members),
        source_build_assignments=len(source_assignments),
        duplicate_build_assignments=duplicate_assignments,
        conflicts=tuple(dict.fromkeys(conflicts)),
    )


def _merge_assignment_rows(
    catalog: dict[str, Any],
    source_team: str,
    destination_team: str,
) -> tuple[dict[str, Any], int, int]:
    source_key = source_team.casefold()
    destination_key = destination_team.casefold()
    updated = deepcopy(catalog)
    assignments = [row for row in updated.get("team_assignments", []) if isinstance(row, dict)]

    kept: list[dict[str, Any]] = []
    destination_by_build: dict[str, dict[str, Any]] = {}
    source_rows: list[dict[str, Any]] = []

    for row in assignments:
        team_key = _text(row.get("team_name")).casefold()
        if team_key == source_key:
            source_rows.append(row)
            continue
        kept.append(row)
        if team_key == destination_key and _text(row.get("build_id")):
            destination_by_build.setdefault(_text(row.get("build_id")), row)

    moved = 0
    collapsed = 0
    for source in source_rows:
        build_id = _text(source.get("build_id"))
        destination = destination_by_build.get(build_id)
        if destination is not None:
            collapsed += 1
            for field in ("raid_role", "slot_name", "status"):
                if not _text(destination.get(field)) and _text(source.get(field)):
                    destination[field] = _text(source.get(field))
            source_notes = _text(source.get("notes"))
            destination_notes = _text(destination.get("notes"))
            if source_notes and source_notes.casefold() not in destination_notes.casefold():
                destination["notes"] = " · ".join(
                    piece for piece in (destination_notes, source_notes) if piece
                )
            continue

        moved_row = deepcopy(source)
        moved_row["team_name"] = destination_team
        # Canonical assignment identity is derived from destination team + build.
        moved_row["assignment_id"] = ""
        kept.append(moved_row)
        if build_id:
            destination_by_build[build_id] = moved_row
        moved += 1

    updated["team_assignments"] = kept
    return updated, moved, collapsed


def _merged_destination_values(roster_service, source_row, destination_row) -> dict[str, str]:
    """Keep destination schedule as one coherent unit; fill only missing state."""
    source_schedule = roster_service.get_team_schedule(str(source_row["name"]))
    destination_schedule = roster_service.get_team_schedule(str(destination_row["name"]))
    destination_has_schedule = bool(destination_schedule and destination_schedule.effective_slots)

    if destination_has_schedule:
        raid_days = _text(destination_row["raid_days"])
        raid_time = _text(destination_row["raid_time"])
        raid_schedule_json = _text(destination_row["raid_schedule_json"])
    else:
        raid_days = _text(source_row["raid_days"])
        raid_time = _text(source_row["raid_time"])
        raid_schedule_json = _text(source_row["raid_schedule_json"])

    return {
        "raid_days": raid_days,
        "raid_time": raid_time,
        "raid_schedule_json": raid_schedule_json,
        "timezone": _text(destination_row["timezone"]) or _text(source_row["timezone"]),
        "current_focus": _text(destination_row["current_focus"]) or _text(source_row["current_focus"]),
    }


def merge_teams(
    roster_service,
    build_service: BuildService,
    source_team: str,
    destination_team: str,
) -> TeamMergeResult:
    preview = preview_team_merge(roster_service, build_service, source_team, destination_team)
    source_name = preview.source_team
    destination_name = preview.destination_team

    source_row = _team_row(roster_service, source_name)
    destination_row = _team_row(roster_service, destination_name)
    if source_row is None or destination_row is None:
        raise RuntimeError("Team state changed before the merge could start. Refresh and try again.")

    catalog_service = build_service.canonical.catalog_service
    catalog_path = Path(catalog_service.catalog_path)
    catalog_existed = catalog_path.exists()
    catalog_backup = catalog_path.read_text(encoding="utf-8") if catalog_existed else ""
    catalog = catalog_service.load()
    updated_catalog, moved_assignments, collapsed_assignments = _merge_assignment_rows(
        catalog,
        source_name,
        destination_name,
    )
    destination_values = _merged_destination_values(roster_service, source_row, destination_row)

    connection = roster_service.db.connection
    connection.execute("SAVEPOINT bff_team_merge")
    try:
        # Save canonical build-assignment movement first. If SQLite fails, the
        # exact prior catalog file is restored below so the merge is retryable.
        if updated_catalog != catalog:
            catalog_service.save(updated_catalog)

        connection.execute(
            """
            INSERT OR IGNORE INTO team_member (roster_member_id, team_id)
            SELECT roster_member_id, ?
            FROM team_member
            WHERE team_id = ?
            """,
            (int(destination_row["id"]), int(source_row["id"])),
        )
        connection.execute(
            """
            UPDATE team
            SET raid_days = ?, raid_time = ?, timezone = ?, raid_schedule_json = ?, current_focus = ?
            WHERE id = ?
            """,
            (
                destination_values["raid_days"],
                destination_values["raid_time"],
                destination_values["timezone"],
                destination_values["raid_schedule_json"],
                destination_values["current_focus"],
                int(destination_row["id"]),
            ),
        )
        connection.execute(
            "DELETE FROM team_member WHERE team_id = ?",
            (int(source_row["id"]),),
        )
        connection.execute("DELETE FROM team WHERE id = ?", (int(source_row["id"]),))
        connection.execute("RELEASE SAVEPOINT bff_team_merge")
    except Exception:
        connection.execute("ROLLBACK TO SAVEPOINT bff_team_merge")
        connection.execute("RELEASE SAVEPOINT bff_team_merge")
        if catalog_existed:
            catalog_path.parent.mkdir(parents=True, exist_ok=True)
            catalog_path.write_text(catalog_backup, encoding="utf-8")
        elif catalog_path.exists():
            catalog_path.unlink()
        raise

    return TeamMergeResult(
        source_team=source_name,
        destination_team=destination_name,
        moved_memberships=preview.memberships_to_move,
        collapsed_memberships=preview.duplicate_memberships,
        moved_build_assignments=moved_assignments,
        collapsed_build_assignments=collapsed_assignments,
        conflicts=preview.conflicts,
    )


class TeamMergeDialog(QDialog):
    def __init__(
        self,
        roster_service,
        build_service: BuildService,
        *,
        preferred_source: str = "",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.roster_service = roster_service
        self.build_service = build_service
        self.setWindowTitle("Merge Teams")
        self.setMinimumWidth(620)
        self.resize(700, 460)

        root = QVBoxLayout(self)
        intro = QLabel(
            "Move one team's roster memberships and canonical build assignments into another team. "
            "The destination survives; the source team is deleted only after the transfer succeeds."
        )
        intro.setWordWrap(True)
        intro.setProperty("pageSubtitle", True)
        root.addWidget(intro)

        form = QFormLayout()
        self.source_combo = QComboBox()
        self.destination_combo = QComboBox()
        names = roster_service.list_team_names()
        self.source_combo.addItems(names)
        self.destination_combo.addItems(names)
        form.addRow("FROM / SOURCE", self.source_combo)
        form.addRow("INTO / DESTINATION", self.destination_combo)
        root.addLayout(form)

        if preferred_source:
            source_index = next(
                (i for i, name in enumerate(names) if name.casefold() == preferred_source.casefold()),
                -1,
            )
            if source_index >= 0:
                self.source_combo.setCurrentIndex(source_index)
        self._choose_different_destination()

        self.summary = QLabel()
        self.summary.setWordWrap(True)
        root.addWidget(self.summary)

        conflict_heading = QLabel("CONFLICTS / DESTINATION WINS")
        conflict_heading.setProperty("sidebarHeading", True)
        root.addWidget(conflict_heading)
        self.conflicts = QPlainTextEdit()
        self.conflicts.setReadOnly(True)
        self.conflicts.setMaximumHeight(150)
        root.addWidget(self.conflicts)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok
        )
        self.merge_button = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        self.merge_button.setText("Merge Teams")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        root.addWidget(self.buttons)

        self.source_combo.currentTextChanged.connect(self._selection_changed)
        self.destination_combo.currentTextChanged.connect(self._selection_changed)
        self._refresh_preview()

    def _choose_different_destination(self) -> None:
        source = self.source_combo.currentText().strip().casefold()
        for index in range(self.destination_combo.count()):
            if self.destination_combo.itemText(index).strip().casefold() != source:
                self.destination_combo.setCurrentIndex(index)
                return

    def _selection_changed(self, *_args) -> None:
        if (
            self.source_combo.currentText().strip().casefold()
            == self.destination_combo.currentText().strip().casefold()
        ):
            self._choose_different_destination()
        self._refresh_preview()

    def _refresh_preview(self) -> None:
        source = self.source_combo.currentText().strip()
        destination = self.destination_combo.currentText().strip()
        try:
            preview = preview_team_merge(
                self.roster_service,
                self.build_service,
                source,
                destination,
            )
        except Exception as exc:
            self.summary.setText(str(exc))
            self.conflicts.setPlainText("")
            self.merge_button.setEnabled(False)
            return

        self.merge_button.setEnabled(True)
        self.summary.setText(
            f'"{preview.source_team}" → "{preview.destination_team}"\n\n'
            f"Roster memberships: {preview.source_memberships} in source; "
            f"{preview.memberships_to_move} move, {preview.duplicate_memberships} already exist in destination.\n"
            f"Build assignments: {preview.source_build_assignments} in source; "
            f"{preview.build_assignments_to_move} move, {preview.duplicate_build_assignments} already exist in destination.\n\n"
            "People, characters, and saved builds are never deleted by this merge."
        )
        self.conflicts.setPlainText(
            "\n".join(f"• {line}" for line in preview.conflicts)
            if preview.conflicts
            else "No conflicting schedule, focus, or duplicate build-assignment values detected."
        )

    @property
    def source_team(self) -> str:
        return self.source_combo.currentText().strip()

    @property
    def destination_team(self) -> str:
        return self.destination_combo.currentText().strip()


def _open_merge_dialog(page) -> None:
    names = page.roster_service.list_team_names()
    if len(names) < 2:
        page.status.warning("You need at least two teams before there is anything to merge.")
        return

    build_service = BuildService(get_data_dir() / "builds.json")
    build_service.load()
    preferred = (
        page.schedule_team_combo.currentText().strip()
        if hasattr(page, "schedule_team_combo")
        else ""
    )
    dialog = TeamMergeDialog(
        page.roster_service,
        build_service,
        preferred_source=preferred,
        parent=page,
    )
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return

    if not confirm_destructive_action(
        page,
        title="Confirm Team Merge",
        object_label=f'Merge "{dialog.source_team}" into "{dialog.destination_team}"?',
        impact=(
            "The destination team survives. The source team is removed only after its "
            "roster memberships and canonical build assignments are transferred. "
            "People, characters, and saved builds are kept. A recoverable database "
            "snapshot is created first."
        ),
        confirm_text="Merge Teams",
    ):
        return

    UserSafetySnapshotService().create(
        f"merge-team-{dialog.source_team}-into-{dialog.destination_team}"
    )
    try:
        result = merge_teams(
            page.roster_service,
            build_service,
            dialog.source_team,
            dialog.destination_team,
        )
        page.refresh()
        if hasattr(page, "_reload_schedule_teams"):
            page._reload_schedule_teams(result.destination_team)
        page.status.success(
            f"Merged {result.source_team} into {result.destination_team}: "
            f"{result.moved_memberships} roster membership(s) moved, "
            f"{result.moved_build_assignments} build assignment(s) moved."
        )
        if result.conflicts:
            QMessageBox.information(
                page,
                "Team Merge Notes",
                "The merge completed. Destination values were kept for these conflicts:\n\n"
                + "\n".join(f"• {line}" for line in result.conflicts),
            )
    except Exception as exc:
        page.status.error(f"Team merge failed: {exc}")
        QMessageBox.critical(page, "Team Merge Failed", str(exc))


def _find_layout_containing(layout, target):
    if layout is None:
        return None
    for index in range(layout.count()):
        item = layout.itemAt(index)
        if item.widget() is target:
            return layout
        nested = item.layout()
        found = _find_layout_containing(nested, target) if nested is not None else None
        if found is not None:
            return found
    return None


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.themed_roster_page import RosterPage

    original_build_team_schedule_tab = RosterPage._build_team_schedule_tab

    def build_team_schedule_tab_with_merge(self):
        page = original_build_team_schedule_tab(self)
        delete_button = next(
            (
                button
                for button in page.findChildren(QPushButton)
                if button.text().strip().casefold() == "delete selected team"
            ),
            None,
        )
        if delete_button is not None:
            row_layout = _find_layout_containing(page.layout(), delete_button)
            if row_layout is not None:
                merge_button = QPushButton("Merge Teams…")
                merge_button.setToolTip(
                    "Merge one named team into another while preserving people, characters, builds, and canonical build ownership."
                )
                merge_button.clicked.connect(
                    lambda _checked=False: _open_merge_dialog(self)
                )
                row_layout.insertWidget(
                    max(0, row_layout.indexOf(delete_button)),
                    merge_button,
                )
                self.merge_teams_button = merge_button
        return page

    RosterPage._build_team_schedule_tab = build_team_schedule_tab_with_merge
    _INSTALLED = True
