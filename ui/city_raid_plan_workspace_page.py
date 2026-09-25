from __future__ import annotations

"""Urban Wilderness shell over the canonical Raid Plan editor."""

from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFileDialog,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLayout,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QSizePolicy,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from services.raid_plan_build_export_service import (
    export_raid_plan_builds_csv,
    export_raid_plan_builds_pdf,
    raid_plan_build_export,
    raid_plan_discord_builds_text,
)
from services.raid_plan_offensive_stats_service import RaidPlanOffensiveStatsService
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
        self.team_combo = QComboBox()
        self.team_combo.setMinimumWidth(180)
        self.team_combo.setToolTip(
            "Optional Team assigned to this Raid Plan. Blank keeps the plan ad-hoc."
        )
        self._refresh_team_choices(
            str(getattr(getattr(self, "_loaded_plan_snapshot", None), "team_name", "") or "")
        )
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
        roles_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)

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
            show_plan_editor=False,
            show_team_editor=False,
            show_saved_plan_selector=False,
            action_button_names=(),
            align_right=True,
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

        # FoundryPage already owns the page-level QScrollArea. The content layout
        # must advertise its real minimum height or QStackedWidget will happily
        # compress the bottom of the page into oblivion instead of letting the
        # outer scroll area do its one job.
        self.workspace_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        self.local_stack = QStackedWidget()
        self.local_stack.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.MinimumExpanding,
        )
        self.overview_surface = self._build_overview_surface()
        self.local_stack.addWidget(self.overview_surface)
        self.local_stack.addWidget(roles_surface)

        # Reuse the canonical saved-plan selector. Loading from Roles follows
        # the same guarded path as selecting a plan on the overview.
        roles_plan_picker = QWidget(roles_surface)
        roles_plan_row = QHBoxLayout(roles_plan_picker)
        roles_plan_row.setContentsMargins(0, 0, 0, 0)
        roles_plan_row.setSpacing(8)
        roles_plan_row.addWidget(QLabel("SAVED RAID PLAN"))
        self.saved_plan_combo.setParent(roles_plan_picker)
        self.saved_plan_combo.setToolTip("Choose a saved Raid Plan, then click Load.")
        self.saved_plan_combo.show()
        roles_plan_row.addWidget(self.saved_plan_combo, 1)
        self.load_plan_button.setParent(roles_plan_picker)
        self.load_plan_button.show()
        roles_plan_row.addWidget(self.load_plan_button)
        roles_layout.insertWidget(0, roles_plan_picker)

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
        self.plan_list.itemClicked.connect(self._load_overview_plan)
        self.plan_list.setToolTip(
            "Select a Raid Plan here. Unsaved edits are protected before another plan can load."
        )
        left.addWidget(self.plan_list)

        self.new_identity_panel = QWidget()
        identity_layout = QVBoxLayout(self.new_identity_panel)
        identity_layout.setContentsMargins(0, 0, 0, 0)
        identity_layout.setSpacing(6)

        name_label = QLabel("NEW PLAN NAME")
        name_label.setProperty("sidebarHeading", True)
        identity_layout.addWidget(name_label)
        self.plan_name_edit.setParent(self.new_identity_panel)
        identity_layout.addWidget(self.plan_name_edit)

        team_label = QLabel("TEAM")
        team_label.setProperty("sidebarHeading", True)
        identity_layout.addWidget(team_label)
        self.team_combo.setParent(self.new_identity_panel)
        identity_layout.addWidget(self.team_combo)
        left.addWidget(self.new_identity_panel)

        self.loaded_identity_label = QLabel()
        self.loaded_identity_label.setWordWrap(True)
        self.loaded_identity_label.setProperty("raidSnapshotValue", True)
        left.addWidget(self.loaded_identity_label)

        new_plan = QPushButton("New Plan")
        new_plan.clicked.connect(self._start_new_plan_from_sidebar)
        left.addWidget(new_plan)

        self.rename_plan_button = QPushButton("Rename…")
        self.rename_plan_button.clicked.connect(self._rename_loaded_plan)
        left.addWidget(self.rename_plan_button)

        self.change_team_button = QPushButton("Change Team…")
        self.change_team_button.clicked.connect(self._change_loaded_plan_team)
        left.addWidget(self.change_team_button)

        self.save_plan_button.setParent(left)
        self.save_plan_button.setText("Save")
        self.save_plan_button.setProperty("primary", True)
        left.addWidget(self.save_plan_button)

        self.open_raid_map_button.setParent(left)
        left.addWidget(self.open_raid_map_button)

        self.archive_plan_button.setParent(left)
        left.addWidget(self.archive_plan_button)

        self.publish_plan_finch_button.setParent(left)
        left.addWidget(self.publish_plan_finch_button)

        self.get_shared_plans_button.setParent(left)
        self.get_shared_plans_button.setText("Shared Plans")
        left.addWidget(self.get_shared_plans_button)

        self.delete_plan_button.setParent(left)
        left.addWidget(self.delete_plan_button)

        self.load_plan_button.hide()

        field_note = QLabel("Plan identity changes are explicit. Ordinary edits cannot silently rename or re-home a saved plan.")
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

        offensive = FoundryCard("Critical Damage & Penetration", "crosshair")
        offensive_note = QLabel(
            "Current planned raid values. Crit Damage includes personal standing stats, "
            "planned Force/Lucent/Brittle layers, and the 125% cap. Pen shows personal "
            "Physical/Spell Pen plus planned target Armor reduction against 18,200 PvE Armor."
        )
        offensive_note.setWordWrap(True)
        offensive_note.setProperty("muted", True)
        offensive.addWidget(offensive_note)
        self.offensive_stats_table = QTableWidget(0, 8)
        self.offensive_stats_table.setHorizontalHeaderLabels(
            (
                "SEAT / PLAYER",
                "CLASS",
                "PERSONAL CRIT",
                "RAID CRIT",
                "PHYS PEN",
                "SPELL PEN",
                "RAID ARMOR ↓",
                "EFFECTIVE P / S",
            )
        )
        self.offensive_stats_table.verticalHeader().setVisible(False)
        self.offensive_stats_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.offensive_stats_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.offensive_stats_table.setMinimumHeight(265)
        self.offensive_stats_table.setToolTip(
            "Hover a value for its contribution ledger and unresolved evidence."
        )
        offensive.addWidget(self.offensive_stats_table)
        self.offensive_stats_summary = QLabel("Save and load a Raid Plan to calculate the team.")
        self.offensive_stats_summary.setWordWrap(True)
        self.offensive_stats_summary.setProperty("muted", True)
        offensive.addWidget(self.offensive_stats_summary)
        center_layout.addWidget(offensive)

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
        loaded = getattr(self, "_loaded_plan_snapshot", None)
        current = getattr(loaded, "plan_id", None)
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
        self._refresh_plan_identity_ui()
        if plan is None:
            self._refresh_trial_banner()
            self.overview_hero.setText("No saved Raid Plan yet. Use Roles to assemble one without inventing missing identity.")
            for card in (self.team_snapshot, self.encounter_snapshot, self.strategy_snapshot, self.progress_snapshot):
                card.value_label.setText("—")
            self._clear_offensive_stats("Save and load a Raid Plan to calculate the team.")
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
        self._refresh_offensive_stats(plan)

    @staticmethod
    def _offensive_stat_tooltip(row) -> str:
        lines = [
            f"{row.seat_id} · {row.player_label}",
            f"Class: {row.eso_class or 'Unknown'}",
        ]
        if row.personal_critical_damage is not None:
            lines.append(f"Personal Critical Damage: {row.personal_critical_damage * 100:.1f}%")
        if row.raid_critical_damage is not None:
            lines.append(f"Raid-adjusted Critical Damage: {row.raid_critical_damage * 100:.1f}%")
        if row.physical_penetration is not None:
            lines.append(f"Physical Penetration: {row.physical_penetration:,.0f}")
        if row.spell_penetration is not None:
            lines.append(f"Spell Penetration: {row.spell_penetration:,.0f}")
        lines.append(f"Raid target Armor reduction: {row.raid_armor_reduction:,.0f}")
        if row.physical_overpenetration is not None:
            label = "over" if row.physical_overpenetration >= 0 else "short"
            lines.append(f"Physical: {abs(row.physical_overpenetration):,.0f} {label} of 18,200")
        if row.spell_overpenetration is not None:
            label = "over" if row.spell_overpenetration >= 0 else "short"
            lines.append(f"Spell: {abs(row.spell_overpenetration):,.0f} {label} of 18,200")

        if row.contributions:
            lines.append("")
            lines.append("Contributions:")
            for contribution in row.contributions:
                suffix = " (conditional/planned)" if contribution.conditional else ""
                if "critical" in contribution.kind:
                    value = (
                        f"{contribution.value * 100:+.1f}%"
                        if abs(contribution.value) <= 2.0
                        else f"{contribution.value:+,.0f}"
                    )
                elif "multiplier" in contribution.kind:
                    value = f"×{contribution.value:.3f}"
                else:
                    value = f"{contribution.value:+,.0f}"
                lines.append(f"  {contribution.label}: {value}{suffix}")
        if row.unresolved:
            lines.append("")
            lines.append("Unresolved / not assumed:")
            lines.extend(f"  {message}" for message in row.unresolved[:12])
            if len(row.unresolved) > 12:
                lines.append(f"  … {len(row.unresolved) - 12} more")
        return "\n".join(lines)

    def _clear_offensive_stats(self, message: str) -> None:
        if not hasattr(self, "offensive_stats_table"):
            return
        self.offensive_stats_table.setRowCount(0)
        self.offensive_stats_summary.setText(message)

    def _refresh_offensive_stats(self, plan) -> None:
        if not hasattr(self, "offensive_stats_table"):
            return
        try:
            service = getattr(self, "_offensive_stats_service", None)
            if service is None:
                service = RaidPlanOffensiveStatsService()
                self._offensive_stats_service = service
            result = service.calculate(plan)
        except Exception as exc:
            self._clear_offensive_stats(f"Crit / Pen calculation unavailable: {exc}")
            return

        table = self.offensive_stats_table
        table.setRowCount(len(result.rows))
        resolved = 0
        capped = 0
        for row_index, stat in enumerate(result.rows):
            if stat.resolved:
                resolved += 1
            if stat.critical_capped:
                capped += 1
            player = stat.player_label or stat.seat_id
            labels = (
                f"{stat.seat_id} · {player}",
                stat.eso_class or "—",
                "—" if stat.personal_critical_damage is None else f"{stat.personal_critical_damage * 100:.1f}%",
                "—" if stat.raid_critical_damage is None else (
                    f"{stat.raid_critical_damage * 100:.1f}%"
                    + (" CAP" if stat.critical_capped else "")
                ),
                "—" if stat.physical_penetration is None else f"{stat.physical_penetration:,.0f}",
                "—" if stat.spell_penetration is None else f"{stat.spell_penetration:,.0f}",
                f"{stat.raid_armor_reduction:,.0f}",
                "—" if stat.effective_physical_penetration is None else (
                    f"{stat.effective_physical_penetration:,.0f} / "
                    f"{stat.effective_spell_penetration:,.0f}"
                ),
            )
            tooltip = self._offensive_stat_tooltip(stat)
            for column, label in enumerate(labels):
                item = QTableWidgetItem(label)
                item.setToolTip(tooltip)
                table.setItem(row_index, column, item)

        table.resizeColumnsToContents()
        remaining = max(0.0, result.target_resistance - result.raid_armor_reduction)
        summary = (
            f"{resolved}/{len(result.rows)} builds resolved · "
            f"{capped} at 125% raid Crit Damage cap · "
            f"Raid Armor reduction {result.raid_armor_reduction:,.0f} · "
            f"{remaining:,.0f} personal Pen needed vs 18,200"
        )
        if result.unresolved:
            summary += f" · {len(result.unresolved)} raid effect(s) left fail-closed"
        self.offensive_stats_summary.setText(summary)
        self.offensive_stats_summary.setToolTip(
            "\n".join(result.unresolved[:20]) if result.unresolved else ""
        )

    def _refresh_plan_identity_ui(self) -> None:
        if not hasattr(self, "new_identity_panel"):
            return
        plan = getattr(self, "_loaded_plan_snapshot", None)
        is_new = plan is None
        self.new_identity_panel.setVisible(is_new)
        self.loaded_identity_label.setVisible(not is_new)
        self.rename_plan_button.setVisible(not is_new)
        self.change_team_button.setVisible(not is_new)

        if is_new:
            self.plan_name_edit.show()
            self.team_combo.show()
            self.loaded_identity_label.clear()
            return

        self.plan_name_edit.hide()
        self.team_combo.hide()
        team = str(getattr(plan, "team_name", "") or "").strip() or "No Team"
        self.loaded_identity_label.setText(
            f"{plan.name}\nTeam: {team}\n{self._trial_display_for(plan)} • "
            f"{plan.difficulty or 'Difficulty not set'}"
        )

    def _start_new_plan_from_sidebar(self) -> None:
        if self.has_pending_changes() and not self.discard_pending_changes():
            return
        self._loaded_plan_snapshot = None
        RaidPlanAdviserPage.clear_plan(self)
        self.plan_name_edit.setText("New Raid Plan")
        self._refresh_team_choices("")
        self.saved_plan_combo.blockSignals(True)
        index = self.saved_plan_combo.findData("__new_plan__")
        if index >= 0:
            self.saved_plan_combo.setCurrentIndex(index)
        self.saved_plan_combo.blockSignals(False)
        self._navigation_baseline_plan = self.current_plan()
        self._refresh_plan_identity_ui()
        self._refresh_overview()
        self.plan_name_edit.setFocus()
        self.plan_name_edit.selectAll()
        self.status.info("New Raid Plan ready. Name it, choose a Team if needed, then Save.")

    def _rename_loaded_plan(self) -> None:
        plan = getattr(self, "_loaded_plan_snapshot", None)
        if plan is None:
            self.status.warning("Save the new Raid Plan before renaming it.")
            return
        if self.has_pending_changes() and not self.save_pending_changes():
            self.status.warning("Save or discard content edits before renaming this Raid Plan.")
            return
        new_name, ok = QInputDialog.getText(
            self,
            "Rename Raid Plan",
            "Raid Plan name:",
            text=plan.name,
        )
        new_name = " ".join(str(new_name or "").strip().split())
        if not ok or not new_name or new_name == plan.name:
            return
        updated = replace(plan, name=new_name)
        try:
            self.plan_repository.save(updated, expected=plan)
        except Exception as exc:
            self.status.error(f"Could not rename Raid Plan: {exc}")
            return
        self.apply_plan(updated)
        self.refresh_saved_plan_picker(select_plan_id=updated.plan_id)
        self._refresh_overview()
        self.status.success(f'Renamed Raid Plan to "{updated.name}".')

    def _change_loaded_plan_team(self) -> None:
        plan = getattr(self, "_loaded_plan_snapshot", None)
        if plan is None:
            self.status.warning("Choose the Team while creating the new Raid Plan.")
            return
        if self.has_pending_changes() and not self.save_pending_changes():
            self.status.warning("Save or discard content edits before changing Team ownership.")
            return
        try:
            team_names = tuple(self.roster_service.list_team_names())
        except Exception as exc:
            self.status.error(f"Could not load Teams: {exc}")
            return

        labels = ("No Team",) + team_names
        current = plan.team_name or "No Team"
        current_index = labels.index(current) if current in labels else 0
        selected, ok = QInputDialog.getItem(
            self,
            "Change Raid Plan Team",
            "Team:",
            labels,
            current_index,
            False,
        )
        if not ok:
            return
        new_team = "" if selected == "No Team" else str(selected)
        old_team = plan.team_name or "No Team"
        if (new_team or "No Team") == old_team:
            return

        answer = QMessageBox.question(
            self,
            "Change Raid Plan Team",
            (
                f'Change Team for "{plan.name}"?\n\n'
                f"Current Team: {old_team}\n"
                f"New Team: {new_team or 'No Team'}\n\n"
                "This changes the Team attached to this saved Raid Plan. "
                "It does not rename, merge, or delete either Team."
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        updated = replace(plan, team_name=new_team or None)
        try:
            self.plan_repository.save(updated, expected=plan)
        except Exception as exc:
            self.status.error(f"Could not change Raid Plan Team: {exc}")
            return
        self.apply_plan(updated)
        self.refresh_saved_plan_picker(select_plan_id=updated.plan_id)
        self._refresh_overview()
        self.status.success(
            f'Raid Plan "{updated.name}" now belongs to {updated.team_name or "No Team"}.'
        )

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

    def _refresh_team_choices(self, preferred: str = "") -> None:
        if not hasattr(self, "team_combo"):
            return
        wanted = str(preferred or "").strip()
        current = str(self.team_combo.currentData() or "").strip()
        if not wanted:
            wanted = current

        self.team_combo.blockSignals(True)
        self.team_combo.clear()
        self.team_combo.addItem("No Team", "")
        try:
            names = self.roster_service.list_team_names()
        except Exception:
            names = []
        for name in names:
            self.team_combo.addItem(name, name)
        index = self.team_combo.findData(wanted) if wanted else 0
        self.team_combo.setCurrentIndex(index if index >= 0 else 0)
        self.team_combo.blockSignals(False)

    def current_plan(self):
        plan = super().current_plan()
        note = self.plan_notes.toPlainText().strip() if hasattr(self, "plan_notes") else ""
        team_name = (
            str(self.team_combo.currentData() or "").strip()
            if hasattr(self, "team_combo")
            else str(getattr(plan, "team_name", "") or "").strip()
        )
        return replace(
            plan,
            team_name=team_name or None,
            plan_note=note or None,
        )

    def apply_plan(self, plan) -> None:
        super().apply_plan(plan)
        if hasattr(self, "team_combo"):
            self._refresh_team_choices(str(getattr(plan, "team_name", "") or ""))
        if hasattr(self, "plan_notes"):
            self.plan_notes.setPlainText(str(getattr(plan, "plan_note", "") or ""))
        self._navigation_baseline_plan = plan
        self._refresh_plan_identity_ui()

    def clear_plan(self) -> None:
        super().clear_plan()
        if hasattr(self, "team_combo"):
            self._refresh_team_choices("")
            self.team_combo.setCurrentIndex(0)
        if hasattr(self, "plan_notes"):
            self.plan_notes.clear()
        self._refresh_plan_identity_ui()

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
        if self.save_current_plan() is not None:
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
