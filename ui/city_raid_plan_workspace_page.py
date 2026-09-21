from __future__ import annotations

"""Urban Wilderness shell over the canonical Raid Plan editor."""

from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QPlainTextEdit,
    QStackedWidget,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from services.raid_plan_build_export_service import (
    export_raid_plan_builds_csv,
    export_raid_plan_builds_pdf,
    raid_plan_build_export,
    raid_plan_discord_builds_text,
)
from ui.components.foundry_card import FoundryCard
from ui.raid_plan_adviser_page import RaidPlanAdviserPage
from ui.raid_plan_header_controls import rehome_plan_header_controls
from ui.raid_trial_banner_support import TrialBannerLabel, trial_banner_path


def _foundry_card_ancestor(widget: QWidget | None) -> QWidget | None:
    current = widget
    while current is not None:
        if bool(current.property("foundryCard")):
            return current
        current = current.parentWidget()
    return None


class _TrialBannerLabel(QLabel):
    """Crop a wide trial image to the available hero slot without distortion."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._source_pixmap = QPixmap()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumHeight(132)
        self.setMaximumHeight(168)
        self.setMinimumWidth(260)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setProperty("raidPlanTrialBanner", True)

    def set_source(self, path: Path | None) -> None:
        self._source_pixmap = QPixmap(str(path)) if path is not None else QPixmap()
        self.setVisible(not self._source_pixmap.isNull())
        self._refresh_pixmap()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._refresh_pixmap()

    def _refresh_pixmap(self) -> None:
        if self._source_pixmap.isNull() or self.width() <= 0 or self.height() <= 0:
            self.clear()
            return
        scaled = self._source_pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = max(0, (scaled.width() - self.width()) // 2)
        y = max(0, (scaled.height() - self.height()) // 2)
        width = min(self.width(), scaled.width())
        height = min(self.height(), scaled.height())
        self.setPixmap(scaled.copy(x, y, width, height))


class CityRaidPlanWorkspacePage(RaidPlanAdviserPage):
    """Raid Plan overview + focused Roles editor using one underlying RaidPlan model."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._compose_city_shell()
        self._replace_legacy_role_language(self)
        self._refresh_overview()

    def _compose_city_shell(self) -> None:
        self.header.title.setText("Raid Plan")
        self.header.subtitle.setText("Turn a group of good players into a great run.")
        self.header.department.setText("RAID • PLAN")

        self.share_builds_button = QPushButton("Share Builds ▾")
        self.share_builds_button.setToolTip(
            "Share this Raid Plan's resolved builds as an ink-light PDF, CSV, or Discord text."
        )
        share_menu = QMenu(self.share_builds_button)
        pdf_action = share_menu.addAction("Export Ink-Light PDF")
        csv_action = share_menu.addAction("Export CSV")
        share_menu.addSeparator()
        discord_action = share_menu.addAction("Copy for Discord")
        pdf_action.triggered.connect(self._export_plan_builds_pdf)
        csv_action.triggered.connect(self._export_plan_builds_csv)
        discord_action.triggered.connect(self._copy_plan_builds_discord)
        self.share_builds_button.setMenu(share_menu)

        # Preserve canonical role/spot controls without adding another decorative
        # field-note card above them. Duties live on the dedicated Assignments page.
        roles_surface = QWidget()
        roles_layout = QVBoxLayout(roles_surface)
        roles_layout.setContentsMargins(0, 0, 0, 0)
        roles_layout.setSpacing(8)

        while self.workspace_layout.count():
            item = self.workspace_layout.takeAt(0)
            if item.widget() is not None:
                roles_layout.addWidget(item.widget())
            elif item.layout() is not None:
                roles_layout.addLayout(item.layout())
        self.roles_surface = roles_surface

        plan_context_bar = rehome_plan_header_controls(
            self,
            trailing_widgets=(self.share_builds_button,),
        )

        assignment_card = _foundry_card_ancestor(getattr(self, "assignment_table", None))
        if assignment_card is not None:
            assignment_card.hide()

        nav_host = QWidget()
        nav = QHBoxLayout(nav_host)
        nav.setContentsMargins(0, 0, 0, 0)
        nav.setSpacing(5)
        self.context_buttons: dict[str, QPushButton] = {}
        routes = (
            ("Overview", None),
            ("Roles", None),
            ("Assignments", "assignments"),
            ("Comp Builder", "comp_builder"),
            ("Builds", "console:2"),
            ("Rotations", "rotations"),
            ("Coverage", "console:7"),
            ("Strategy", "console:4"),
            ("Readiness", "readiness"),
            ("Run", "live_raid"),
            ("Review", "raid_review"),
        )
        for title, route in routes:
            button = QPushButton(title)
            button.setCheckable(route is None)
            if title == "Overview":
                button.clicked.connect(lambda _=False: self._show_local_view(0))
            elif title == "Roles":
                button.clicked.connect(lambda _=False: self._show_local_view(1))
            else:
                button.clicked.connect(lambda _=False, target=route: self.pageRequested.emit(target))
            nav.addWidget(button)
            self.context_buttons[title] = button
        self.workspace_layout.addWidget(plan_context_bar)
        self.workspace_layout.addWidget(nav_host)

        self.local_stack = QStackedWidget()
        self.overview_surface = self._build_overview_surface()
        self.local_stack.addWidget(self.overview_surface)
        self.local_stack.addWidget(roles_surface)
        self.workspace_layout.addWidget(self.local_stack, 1)
        self._show_local_view(0)
        self.trial_combo.currentTextChanged.connect(self._trial_selection_changed)

    def _build_overview_surface(self) -> QWidget:
        page = QWidget()
        root = QHBoxLayout(page)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        left = FoundryCard("My Plans", "archive")
        self.plan_list = QListWidget()
        self.plan_list.itemDoubleClicked.connect(self._load_overview_plan)
        left.addWidget(self.plan_list)
        field_note = QLabel("Plans are just stories we tell ourselves before the interesting part.")
        field_note.setWordWrap(True)
        field_note.setProperty("muted", True)
        left.addWidget(field_note)
        root.addWidget(left, 2)

        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(8)

        hero = FoundryCard("Selected Plan", "trial")
        hero_row = QWidget()
        hero_layout = QHBoxLayout(hero_row)
        hero_layout.setContentsMargins(0, 0, 0, 0)
        hero_layout.setSpacing(12)
        self.overview_art = TrialBannerLabel()
        self.overview_art.hide()
        hero_layout.addWidget(self.overview_art, 3)
        self.overview_hero = QLabel("No saved plan selected.")
        self.overview_hero.setProperty("heroTitle", True)
        self.overview_hero.setWordWrap(True)
        self.overview_hero.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        hero_layout.addWidget(self.overview_hero, 5)
        hero.addWidget(hero_row)
        center_layout.addWidget(hero)

        snapshot = QGridLayout()
        self.team_snapshot = self._snapshot_card("Team")
        self.encounter_snapshot = self._snapshot_card("Encounter")
        self.strategy_snapshot = self._snapshot_card("Strategy")
        self.progress_snapshot = self._snapshot_card("Progress")
        for index, card in enumerate((self.team_snapshot, self.encounter_snapshot, self.strategy_snapshot, self.progress_snapshot)):
            snapshot.addWidget(card, 0, index)
        center_layout.addLayout(snapshot)

        middle = QHBoxLayout()
        quick = FoundryCard("Quick Actions", "warning")
        edit_roles = QPushButton("Manage Roles / Spots")
        edit_roles.clicked.connect(lambda: self._show_local_view(1))
        quick.addWidget(edit_roles)
        for title, route in (
            ("Edit Assignments", "assignments"),
            ("Check Coverage", "console:7"),
            ("Open Readiness", "readiness"),
            ("Create Run Sheet", "live_raid"),
        ):
            button = QPushButton(title)
            button.clicked.connect(lambda _=False, target=route: self.pageRequested.emit(target))
            quick.addWidget(button)
        save = QPushButton("Save Current Plan")
        save.setProperty("primary", True)
        save.clicked.connect(self._save_from_overview)
        quick.addWidget(save)
        middle.addWidget(quick, 2)

        notes = FoundryCard("Plan Note", "feather")
        notes.setProperty("parchment", True)
        notes.set_watermark("compass", 0.12)
        self.plan_notes = QPlainTextEdit()
        self.plan_notes.setPlaceholderText("If it matters, write it down.")
        self.plan_notes.setProperty("parchmentEditor", True)
        self.plan_notes.setMinimumHeight(126)
        self.plan_notes.setMaximumHeight(160)
        self.plan_notes.setToolTip(
            "Saved with this Raid Plan. Loading another plan restores its own note."
        )
        notes.addWidget(self.plan_notes)
        middle.addWidget(notes, 4)

        timeline = FoundryCard("Timeline", "stopwatch")
        self.timeline_label = QLabel("PLANNED\nPlan created\nRoles selected\nAssignments reviewed\nReadiness checked\nFirst run")
        self.timeline_label.setWordWrap(True)
        timeline.addWidget(self.timeline_label)
        middle.addWidget(timeline, 3)
        center_layout.addLayout(middle)

        lower = QHBoxLayout()
        recent = FoundryCard("Recent Activity", "archive")
        self.recent_label = QLabel("Saved RaidPlan snapshots are the durable activity boundary on this surface.")
        self.recent_label.setWordWrap(True)
        recent.addWidget(self.recent_label)
        lower.addWidget(recent, 1)
        linked = FoundryCard("Linked Resources", "clipboard")
        for title, route in (
            ("Comp Builder", "comp_builder"),
            ("Builds", "console:2"),
            ("Rotation Builder", "rotations"),
            ("Coverage", "console:7"),
            ("Optimizer Adviser", "console:6"),
        ):
            button = QPushButton(title)
            button.clicked.connect(lambda _=False, target=route: self.pageRequested.emit(target))
            linked.addWidget(button)
        lower.addWidget(linked, 1)
        center_layout.addLayout(lower)
        root.addWidget(center, 7)
        return page

    @staticmethod
    def _snapshot_card(title: str) -> FoundryCard:
        card = FoundryCard(title, "compass")
        label = QLabel("—")
        label.setWordWrap(True)
        label.setProperty("raidSnapshotValue", True)
        card.addWidget(label)
        card.value_label = label
        return card

    def _refresh_trial_banner(self) -> None:
        if not hasattr(self, "overview_art") or not hasattr(self, "trial_combo"):
            return
        self.overview_art.set_source(trial_banner_path(self.trial_combo.currentText()))

    def _trial_selection_changed(self, _text: str = "") -> None:
        # Trial selection owns the hero art immediately. The full overview refresh
        # can then update plan metadata without making image selection incidental.
        self._refresh_trial_banner()
        self._refresh_overview()

    def _show_local_view(self, index: int) -> None:
        self.local_stack.setCurrentIndex(index)
        self.context_buttons["Overview"].setChecked(index == 0)
        self.context_buttons["Roles"].setChecked(index == 1)
        if index == 0:
            self._refresh_overview()

    def _refresh_overview(self) -> None:
        if not hasattr(self, "plan_list"):
            return
        current = self.saved_plan_combo.currentData() if hasattr(self, "saved_plan_combo") else None
        plans = self.plan_repository.list_plans()
        self.plan_list.clear()
        selected_item = None
        for plan in plans:
            item = QListWidgetItem(f"{plan.name}\n{plan.trial_id} · {plan.status.title()}")
            item.setData(Qt.ItemDataRole.UserRole, plan.plan_id)
            self.plan_list.addItem(item)
            if current and plan.plan_id == current:
                selected_item = item
        if selected_item is not None:
            self.plan_list.setCurrentItem(selected_item)
        plan = self._loaded_plan_snapshot
        if plan is None and plans:
            plan = plans[0]
        if plan is None:
            self._refresh_trial_banner()
            self.overview_hero.setText("No saved Raid Plan yet. Use Roles to assemble one without inventing missing identity.")
            for card in (self.team_snapshot, self.encounter_snapshot, self.strategy_snapshot, self.progress_snapshot):
                card.value_label.setText("—")
            return
        assigned = sum(1 for member in plan.members if member.primary_assignment or member.secondary_assignment)
        builds = sum(1 for member in plan.members if member.build_selected)
        selected_trial = self.trial_combo.currentText() if hasattr(self, "trial_combo") else ""
        self.overview_art.set_source(
            trial_banner_path(selected_trial, plan.trial_id, plan.name)
        )
        self.overview_hero.setText(
            f"{plan.name}\n{plan.trial_id} · {plan.difficulty or 'Difficulty not set'} · {len(plan.members)} players\nStatus: {plan.status.title()}"
        )
        self.team_snapshot.value_label.setText(plan.team_name or "Ad-hoc team")
        self.encounter_snapshot.value_label.setText(plan.trial_id)
        self.strategy_snapshot.value_label.setText(f"{assigned} / {len(plan.members)} spots assigned")
        self.progress_snapshot.value_label.setText(f"{builds} builds linked")

    def _resolved_plan_build_export(self):
        plan = self.current_plan()
        export = raid_plan_build_export(plan, self.build_service)
        if not export.seats:
            self.status.warning(
                "This Raid Plan has no resolved canonical builds to export yet."
            )
            return plan, None
        return plan, export

    def _export_plan_builds_pdf(self, *_args) -> None:
        plan, export = self._resolved_plan_build_export()
        if export is None:
            return
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Raid Plan Builds",
            f"{plan.name}_builds.pdf",
            "Printer-Friendly PDF (*.pdf)",
        )
        if not filename:
            return
        path = Path(filename)
        if path.suffix.casefold() != ".pdf":
            path = path.with_suffix(".pdf")
        try:
            export_raid_plan_builds_pdf(plan, export, path)
            detail = (
                f" {len(export.unresolved_seats)} unresolved seat(s) were listed separately."
                if export.unresolved_seats
                else ""
            )
            self.status.success(f"Exported ink-light Raid Plan builds to {path}.{detail}")
        except Exception as exc:
            self.status.error(f"Raid Plan PDF export failed: {exc}")

    def _export_plan_builds_csv(self, *_args) -> None:
        plan, export = self._resolved_plan_build_export()
        if export is None:
            return
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Raid Plan Builds",
            f"{plan.name}_builds.csv",
            "CSV Files (*.csv)",
        )
        if not filename:
            return
        path = Path(filename)
        if path.suffix.casefold() != ".csv":
            path = path.with_suffix(".csv")
        try:
            export_raid_plan_builds_csv(plan, export, path)
            self.status.success(f"Exported Raid Plan builds to {path}.")
        except Exception as exc:
            self.status.error(f"Raid Plan CSV export failed: {exc}")

    def _copy_plan_builds_discord(self, *_args) -> None:
        plan, export = self._resolved_plan_build_export()
        if export is None:
            return
        try:
            QApplication.clipboard().setText(
                raid_plan_discord_builds_text(plan, export)
            )
            self.status.success(
                "Copied Raid Plan builds for Discord. Paste directly into the raid channel."
            )
        except Exception as exc:
            self.status.error(f"Discord build copy failed: {exc}")

    def current_plan(self):
        plan = super().current_plan()
        note = self.plan_notes.toPlainText().strip() if hasattr(self, "plan_notes") else ""
        return replace(plan, plan_note=note or None)

    def apply_plan(self, plan) -> None:
        super().apply_plan(plan)
        if hasattr(self, "plan_notes"):
            self.plan_notes.setPlainText(str(getattr(plan, "plan_note", "") or ""))
        self._navigation_baseline_plan = self.current_plan()

    def clear_plan(self) -> None:
        super().clear_plan()
        if hasattr(self, "plan_notes"):
            self.plan_notes.clear()

    def _load_overview_plan(self, item: QListWidgetItem) -> None:
        plan_id = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(plan_id, str):
            return
        index = self.saved_plan_combo.findData(plan_id)
        if index >= 0:
            self.saved_plan_combo.setCurrentIndex(index)
        self.load_selected_plan()
        self._refresh_overview()

    def _save_from_overview(self) -> None:
        self.save_current_plan()
        self._refresh_overview()

    @classmethod
    def _replace_legacy_role_language(cls, root: QWidget) -> None:
        replacements = (("CHAIRS", "ROLES"), ("Chairs", "Roles"), ("chairs", "roles"), ("CHAIR", "ROLE"), ("Chair", "Role"), ("chair", "role"))
        for label in root.findChildren(QLabel):
            text = label.text()
            for old, new in replacements:
                text = text.replace(old, new)
            label.setText(text)
            tip = label.toolTip()
            for old, new in replacements:
                tip = tip.replace(old, new)
            label.setToolTip(tip)
        for button in root.findChildren(QPushButton):
            text = button.text()
            for old, new in replacements:
                text = text.replace(old, new)
            button.setText(text)
            tip = button.toolTip()
            for old, new in replacements:
                tip = tip.replace(old, new)
            button.setToolTip(tip)
        for table in root.findChildren(QTableWidget):
            for column in range(table.columnCount()):
                item = table.horizontalHeaderItem(column)
                if item is None:
                    continue
                text = item.text()
                for old, new in replacements:
                    text = text.replace(old, new)
                item.setText(text)


__all__ = ["CityRaidPlanWorkspacePage"]
