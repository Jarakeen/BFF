from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from engine.config import DEFAULT_DATABASE, get_data_dir
from models.build_model import BuildRoster
from services.build_service import BuildService
from services.saved_build_capability_service import SavedBuildCapabilityService, summarize_raid_coverage
from services.performance_raid_review_runner_service import PerformanceRaidReviewRunnerService
from services.performance_raid_review_selection_mode_service import (
    PerformanceRaidReviewSelectionModeService,
)
from services.raid_coverage_profile import DEFAULT_RAID_COVERAGE_PROFILE
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar
from ui.foundry_page import FoundryPage
from ui.raid_review_async_task import RaidReviewAsyncTask


CORE_COVERAGE = tuple(row.display_name for row in DEFAULT_RAID_COVERAGE_PROFILE.requirements if row.required)
DEBUFFS = {"Major Vulnerability", "Major Breach", "Crusher", "Minor Brittle", "Minor Maim"}
UTILITY = {"Orbs", "Purify", "Magickasteal"}


class CoveragePage(FoundryPage):
    """Buff/debuff planning desk plus observed Raid Review workspace."""

    def __init__(self, parent=None, raid_review_runner=None):
        super().__init__(parent)
        self.build_service = BuildService(get_data_dir() / "builds.json")
        self.capability_service = None
        self.raid_review_runner = raid_review_runner or PerformanceRaidReviewRunnerService()
        self.raid_review_selection_mode_service = PerformanceRaidReviewSelectionModeService()
        self._raid_review_task: RaidReviewAsyncTask | None = None
        self.roster = BuildRoster()
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        self.header = FoundryHeader(
            title="Coverage & Buff Management",
            subtitle="Inspect static build evidence, then review what actually happened in combat.",
            department="Raid Engine • Coverage",
        )
        self.set_header(self.header)

        self.encounter_combo = QComboBox()
        self.encounter_combo.addItem(DEFAULT_RAID_COVERAGE_PROFILE.name)
        self.encounter_combo.setEnabled(False)
        self.encounter_combo.setToolTip("This watch list is fixed; encounter-specific requirements are not connected yet.")
        self.header.add_context_widget(self._context_field("REQUIREMENTS", self.encounter_combo))

        self.tabs = QTabWidget()
        self.tabs.addTab(self._coverage_tab(), "BUFFS & DEBUFFS")
        self.tabs.addTab(self._placeholder("Providers", "Provider reliability and substitutions will live here."), "PROVIDERS")
        self.tabs.addTab(self._raid_review_tab(), "RAID REVIEW")
        self.tabs.addTab(self._placeholder("Encounter Needs", "Encounter-specific required and optional effects will live here."), "ENCOUNTER NEEDS")
        self.tabs.addTab(self._placeholder("Reports", "Coverage exports and historical comparisons will live here."), "REPORTS")
        self.add_workspace(self.tabs)

        self.status = FoundryStatusBar()
        self.set_status(self.status)

    @staticmethod
    def _context_field(title: str, widget: QWidget) -> QWidget:
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        label = QLabel(title)
        label.setProperty("sidebarHeading", True)
        layout.addWidget(label)
        layout.addWidget(widget)
        return box

    def _coverage_tab(self) -> QWidget:
        page = QWidget()
        root = QVBoxLayout(page)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        filters = QHBoxLayout()
        self.effect_filter = QComboBox()
        self.effect_filter.addItems(["All Effects", "Buffs", "Debuffs", "Utility"])
        self.missing_only = QCheckBox("Needs Review Only")
        self.redundant_only = QCheckBox("Multiple Static Sources")
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search effect...")
        filters.addWidget(self.effect_filter)
        filters.addWidget(self.missing_only)
        filters.addWidget(self.redundant_only)
        filters.addStretch(1)
        filters.addWidget(self.search, 1)
        self.effect_filter.currentTextChanged.connect(self._apply_coverage_filters)
        self.missing_only.toggled.connect(self._apply_coverage_filters)
        self.redundant_only.toggled.connect(self._apply_coverage_filters)
        self.search.textChanged.connect(self._apply_coverage_filters)

        table_card = FoundryCard("Saved-Build Coverage Evidence", "◈")
        edit_requirements = QPushButton("Edit Requirements")
        edit_requirements.setEnabled(False)
        edit_requirements.setToolTip("Editing the default coverage requirements is not available yet.")
        table_card.set_header_action(edit_requirements)
        table_card.addLayout(filters)
        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels([
            "Effect", "Type", "Required", "Static Sources", "Planned Provider",
            "Backup", "Target Uptime", "Actual Uptime", "Evidence",
        ])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setMinimumHeight(390)
        table_card.addWidget(self.table)
        root.addWidget(table_card, 4)

        lower = QHBoxLayout()
        lower.setSpacing(8)
        self.summary_card = FoundryCard("Coverage Summary", "✓").set_watermark("compass", 0.055)
        self.providers_card = FoundryCard("Identified Static Sources", "♜").set_watermark("compass", 0.045)
        notes = FoundryCard("Coverage Notes", "✎").make_parchment().set_watermark("feather", 0.11)
        notes.addWidget(QLabel(
            "• This fixed watch list shows only canonically resolved saved-build effects.\n"
            "• Static availability does not assign a player or prove uptime.\n"
            "• Review conditional and unverified effects before planning a pull."
        ))
        lower.addWidget(self.summary_card, 2)
        lower.addWidget(self.providers_card, 2)
        lower.addWidget(notes, 2)
        root.addLayout(lower, 1)
        return page

    def _raid_review_tab(self) -> QWidget:
        page = QWidget()
        root = QVBoxLayout(page)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        intake = FoundryCard("Run Raid Review", "⌕").set_watermark("compass", 0.04)
        intake_row = QHBoxLayout()
        self.raid_review_encounter_combo = QComboBox()
        for encounter in self.raid_review_runner.available_encounters():
            self.raid_review_encounter_combo.addItem(encounter.display_name, encounter.key)
        self.raid_review_encounter_combo.currentIndexChanged.connect(self._raid_review_encounter_changed)
        self.raid_review_report_input = QLineEdit()
        self.raid_review_report_input.setPlaceholderText("ESO Logs report code or report URL")
        self.raid_review_report_input.textChanged.connect(self._raid_review_report_changed)
        self.raid_review_load_fights_button = QPushButton("Load Fights")
        self.raid_review_load_fights_button.clicked.connect(self._load_raid_review_fights)
        self.raid_review_run_button = QPushButton("Run Raid Review")
        self.raid_review_run_button.setProperty("primary", True)
        self.raid_review_run_button.setEnabled(False)
        self.raid_review_run_button.setToolTip(
            "Query the checked encounter fights directly from ESO Logs and compare them as one Raid Review."
        )
        self.raid_review_run_button.clicked.connect(self._run_raid_review)
        intake_row.addWidget(QLabel("ENCOUNTER"))
        intake_row.addWidget(self.raid_review_encounter_combo)
        intake_row.addWidget(QLabel("REPORT"))
        intake_row.addWidget(self.raid_review_report_input, 1)
        intake_row.addWidget(self.raid_review_load_fights_button)
        intake_row.addWidget(self.raid_review_run_button)
        intake.addLayout(intake_row)

        self.raid_review_fights_table = QTableWidget(0, 5)
        self.raid_review_fights_table.setHorizontalHeaderLabels([
            "Use", "Fight", "Result", "Boss %", "Duration",
        ])
        self.raid_review_fights_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.raid_review_fights_table.verticalHeader().setVisible(False)
        self.raid_review_fights_table.horizontalHeader().setStretchLastSection(True)
        self.raid_review_fights_table.setMinimumHeight(135)
        self.raid_review_fights_table.itemChanged.connect(self._raid_review_selection_changed)
        intake.addWidget(self.raid_review_fights_table)
        self.raid_review_selection_mode_label = QLabel()
        self.raid_review_selection_mode_label.setWordWrap(True)
        intake.addWidget(self.raid_review_selection_mode_label)
        self._update_raid_review_selection_mode()
        intake.addWidget(QLabel(
            "Choose a supported encounter, load the report, check the pulls you want compared, then run the review. "
            "Fight discovery and analysis both use the ESO Logs API; raw research JSON is not required."
        ))
        root.addWidget(intake)

        self.raid_review_overview_card = FoundryCard("Raid Review", "◈").set_watermark("compass", 0.045)
        self.raid_review_overview_card.addWidget(QLabel(
            "Compare pulls for the selected encounter and surface evidence-backed patterns.\n"
            "Review focuses on what worked, what changed on wipes, and the highest-value next adjustments."
        ))
        root.addWidget(self.raid_review_overview_card)

        upper = QHBoxLayout()
        upper.setSpacing(8)
        self.raid_review_priorities_card = FoundryCard("Top Priorities", "△").set_watermark("compass", 0.04)
        self.raid_review_working_card = FoundryCard("What Is Working", "✓").set_watermark("feather", 0.05)
        self.raid_review_role_focus_card = FoundryCard("Role Focus", "◎").set_watermark("compass", 0.04)
        self.raid_review_priorities_card.addWidget(QLabel("Run or load a Raid Review to see prioritized findings."))
        self.raid_review_working_card.addWidget(QLabel("Successful-pull patterns and non-problems will appear here."))
        self.raid_review_role_focus_card.addWidget(QLabel("Healer, Tank, DPS, and Group focus will appear here."))
        upper.addWidget(self.raid_review_priorities_card, 2)
        upper.addWidget(self.raid_review_working_card, 2)
        upper.addWidget(self.raid_review_role_focus_card, 2)
        root.addLayout(upper)

        self.raid_review_players_card = FoundryCard("Player Review", "♟").set_watermark("feather", 0.04)
        self.raid_review_players_card.addWidget(QLabel(
            "Per-player strengths, highest-value improvements, and supporting evidence will appear here."
        ))
        root.addWidget(self.raid_review_players_card, 2)

        self.raid_review_evidence_card = FoundryCard("Evidence & Unresolved", "✎").make_parchment().set_watermark("feather", 0.08)
        self.raid_review_evidence_card.addWidget(QLabel(
            "Mechanic windows, recovery timing, coverage evidence, and unresolved observations remain auditable here."
        ))
        root.addWidget(self.raid_review_evidence_card)
        return page

    def _raid_review_encounter_key(self) -> str:
        value = self.raid_review_encounter_combo.currentData()
        return str(value or "").strip()

    def _raid_review_encounter_name(self) -> str:
        return self.raid_review_encounter_combo.currentText().strip() or "selected encounter"

    def _raid_review_encounter_changed(self) -> None:
        self.raid_review_fights_table.setRowCount(0)
        self.raid_review_run_button.setEnabled(False)
        self._update_raid_review_selection_mode()

    def _raid_review_report_changed(self) -> None:
        self.raid_review_fights_table.setRowCount(0)
        self.raid_review_run_button.setEnabled(False)
        self._update_raid_review_selection_mode()

    def _raid_review_selection_changed(self) -> None:
        self._update_raid_review_selection_mode()

    def _update_raid_review_selection_mode(self) -> None:
        fight_ids = self._selected_raid_review_fight_ids()
        mode = self.raid_review_selection_mode_service.classify(fight_ids)
        self.raid_review_selection_mode_label.setText(
            f"{mode.display_name} • {mode.note}"
        )

    def _set_raid_review_busy(self, busy: bool) -> None:
        self.raid_review_encounter_combo.setEnabled(not busy)
        self.raid_review_report_input.setEnabled(not busy)
        self.raid_review_fights_table.setEnabled(not busy)
        self.raid_review_load_fights_button.setEnabled(not busy)
        self.raid_review_run_button.setEnabled(
            (not busy) and self.raid_review_fights_table.rowCount() > 0
        )

    def _start_raid_review_task(self, operation, on_success, error_prefix: str) -> bool:
        if self._raid_review_task is not None and self._raid_review_task.isRunning():
            self.status.warning("A Raid Review API operation is already running.")
            return False

        task = RaidReviewAsyncTask(operation, self)
        self._raid_review_task = task
        task.succeeded.connect(on_success)
        task.failed.connect(lambda message: self._raid_review_task_failed(error_prefix, message))
        task.finished.connect(self._raid_review_task_finished)
        self._set_raid_review_busy(True)
        task.start()
        return True

    def _raid_review_task_failed(self, error_prefix: str, message: str) -> None:
        self.status.error(f"{error_prefix}: {message}")

    def _raid_review_task_finished(self) -> None:
        task = self._raid_review_task
        self._raid_review_task = None
        self._set_raid_review_busy(False)
        if task is not None:
            task.deleteLater()

    def _load_raid_review_fights(self) -> None:
        encounter_key = self._raid_review_encounter_key()
        encounter_name = self._raid_review_encounter_name()
        report_code = self.raid_review_report_input.text().strip()
        if not encounter_key:
            self.status.warning("Choose a supported Raid Review encounter first.")
            return
        if not report_code:
            self.status.warning("Enter an ESO Logs report code or report URL first.")
            return

        self.raid_review_fights_table.setRowCount(0)
        self._update_raid_review_selection_mode()
        self.status.info(f"Loading {encounter_name} pulls from ESO Logs...")
        self._start_raid_review_task(
            lambda: self.raid_review_runner.list_fights(encounter_key, report_code),
            self._raid_review_fights_loaded,
            "Could not load Raid Review fights",
        )

    def _raid_review_fights_loaded(self, choices) -> None:
        self.raid_review_fights_table.blockSignals(True)
        try:
            for choice in choices:
                row = self.raid_review_fights_table.rowCount()
                self.raid_review_fights_table.insertRow(row)

                select_item = QTableWidgetItem()
                select_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
                select_item.setCheckState(Qt.CheckState.Checked)
                select_item.setData(Qt.ItemDataRole.UserRole, int(choice.fight_id))
                self.raid_review_fights_table.setItem(row, 0, select_item)

                result_text = "Kill" if choice.kill else "Wipe"
                boss_text = "—" if choice.boss_percentage is None else f"{choice.boss_percentage / 100:.1f}%"
                duration_text = f"{choice.duration_seconds:.1f}s"
                for column, value in enumerate(
                    (str(choice.fight_id), result_text, boss_text, duration_text),
                    start=1,
                ):
                    self.raid_review_fights_table.setItem(row, column, QTableWidgetItem(value))
        finally:
            self.raid_review_fights_table.blockSignals(False)
        self._update_raid_review_selection_mode()

        encounter_name = self._raid_review_encounter_name()
        if choices:
            self.status.success(
                f"Loaded {len(choices)} {encounter_name} pull(s). Uncheck any pulls you do not want compared."
            )
        else:
            self.status.warning(f"No {encounter_name} pulls were found in that report.")

    def _selected_raid_review_fight_ids(self) -> tuple[int, ...]:
        selected: list[int] = []
        for row in range(self.raid_review_fights_table.rowCount()):
            item = self.raid_review_fights_table.item(row, 0)
            if item is None or item.checkState() != Qt.CheckState.Checked:
                continue
            fight_id = item.data(Qt.ItemDataRole.UserRole)
            if fight_id is not None and int(fight_id) > 0:
                selected.append(int(fight_id))
        return tuple(selected)

    def _run_raid_review(self) -> None:
        encounter_key = self._raid_review_encounter_key()
        encounter_name = self._raid_review_encounter_name()
        report_code = self.raid_review_report_input.text().strip()
        if not encounter_key:
            self.status.warning("Choose a supported Raid Review encounter first.")
            return
        if not report_code:
            self.status.warning("Enter an ESO Logs report code or report URL first.")
            return

        fight_ids = self._selected_raid_review_fight_ids()
        mode = self.raid_review_selection_mode_service.classify(fight_ids)
        if not fight_ids:
            self.status.warning(f"Check at least one {encounter_name} pull before running Raid Review.")
            return

        self.status.info(
            f"Running {mode.display_name.lower()} for {len(fight_ids)} selected {encounter_name} pull(s) from ESO Logs..."
        )
        self._start_raid_review_task(
            lambda: self.raid_review_runner.review_report(encounter_key, report_code, fight_ids),
            self._raid_review_result_loaded,
            "Raid Review failed",
        )

    def _raid_review_result_loaded(self, api_result) -> None:
        review = getattr(api_result, "review", None)
        unresolved = tuple(getattr(api_result, "unresolved", ()) or ())
        self.apply_raid_review_result(review, extra_unresolved=unresolved)
        if review is None:
            self.status.warning("Raid Review could not produce a completed review; see Evidence & Unresolved.")

    @staticmethod
    def _review_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        return label

    def apply_raid_review_result(self, result, *, extra_unresolved=()) -> None:
        """Render one completed Raid Review result without owning analysis or fetching."""
        synthesis = getattr(result, "synthesis", None)
        player_summaries = tuple(getattr(result, "player_summaries", ()) or ())
        unresolved = tuple(
            dict.fromkeys(
                (*tuple(getattr(result, "unresolved", ()) or ()), *tuple(extra_unresolved or ()))
            )
        )

        for card in (
            self.raid_review_overview_card,
            self.raid_review_priorities_card,
            self.raid_review_working_card,
            self.raid_review_role_focus_card,
            self.raid_review_players_card,
            self.raid_review_evidence_card,
        ):
            card.clear()

        if synthesis is None:
            self.raid_review_overview_card.addWidget(self._review_label("No completed Raid Review result is available."))
            self.raid_review_priorities_card.addWidget(self._review_label("No priorities available."))
            self.raid_review_working_card.addWidget(self._review_label("No successful-pull patterns available."))
            self.raid_review_role_focus_card.addWidget(self._review_label("No role-focus summary available."))
            self.raid_review_players_card.addWidget(self._review_label("No player summaries available."))
            if unresolved:
                for item in unresolved[:12]:
                    self.raid_review_evidence_card.addWidget(self._review_label(f"• {item}"))
            else:
                self.raid_review_evidence_card.addWidget(self._review_label("No review evidence available."))
            self.status.warning("Raid Review result was unavailable.")
            return

        self.raid_review_overview_card.addWidget(self._review_label(
            f"{synthesis.encounter_name or 'Encounter'}\n"
            f"Pulls {synthesis.pull_count}  •  Kills {synthesis.kill_count}  •  Wipes {synthesis.wipe_count}"
        ))

        priorities = tuple(getattr(synthesis, "top_priorities", ()) or ())
        if priorities:
            for item in priorities:
                self.raid_review_priorities_card.addWidget(self._review_label(
                    f"{item.rank}. {item.title}\n"
                    f"{item.subject} • {str(item.priority).upper()} • {item.evidence}\n"
                    f"Next: {item.recommendation}"
                ))
        else:
            self.raid_review_priorities_card.addWidget(self._review_label("No actionable priorities met the reviewed evidence threshold."))

        working = tuple(getattr(synthesis, "what_is_working", ()) or ())
        if working:
            for finding in working:
                self.raid_review_working_card.addWidget(self._review_label(
                    f"✓ {finding.title}\n{finding.subject} • {finding.evidence}"
                ))
        else:
            self.raid_review_working_card.addWidget(self._review_label("No reviewed positive pattern has enough evidence yet."))

        role_focus = tuple(getattr(synthesis, "role_focus", ()) or ())
        if role_focus:
            for row in role_focus:
                categories = ", ".join(row.categories) if row.categories else "none"
                self.raid_review_role_focus_card.addWidget(self._review_label(
                    f"{row.role}: {row.actionable_count} actionable • {row.note_count} notes\n"
                    f"Evidence: {categories}"
                ))
        else:
            self.raid_review_role_focus_card.addWidget(self._review_label("No role-level concentration is available yet."))

        if player_summaries:
            for summary in player_summaries:
                lines = [
                    f"{summary.actor_label} • {summary.role} • {summary.kill_count}/{summary.pull_count} kills",
                ]
                if summary.improvements:
                    lines.append("Work on: " + " | ".join(item.title for item in summary.improvements))
                if summary.strengths:
                    lines.append("Working: " + " | ".join(item.title for item in summary.strengths))
                if not summary.improvements and not summary.strengths:
                    lines.append("No player-specific reviewed finding met the current evidence threshold.")
                self.raid_review_players_card.addWidget(self._review_label("\n".join(lines)))
        else:
            self.raid_review_players_card.addWidget(self._review_label("No stable player summaries are available for this review."))

        if unresolved:
            for item in unresolved[:12]:
                self.raid_review_evidence_card.addWidget(self._review_label(f"• {item}"))
            if len(unresolved) > 12:
                self.raid_review_evidence_card.addWidget(self._review_label(
                    f"• {len(unresolved) - 12} additional unresolved observations are not shown here."
                ))
        else:
            self.raid_review_evidence_card.addWidget(self._review_label("No unresolved evidence was reported for this review."))

        self.status.info(
            f"Raid Review ready • {synthesis.pull_count} pulls • {len(priorities)} prioritized finding(s)."
        )

    def _placeholder(self, title: str, text: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        card = FoundryCard(title).set_watermark("compass", 0.04)
        card.addWidget(QLabel(text))
        card.addStretch(1)
        layout.addWidget(card)
        return page

    def _apply_coverage_filters(self, *_args) -> None:
        effect_type = self.effect_filter.currentText()
        query = self.search.text().strip().casefold()
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item is None:
                continue
            name = item.text()
            evidence = self.table.item(row, 8).data(Qt.ItemDataRole.UserRole)
            source_count = self.table.item(row, 3).data(Qt.ItemDataRole.UserRole) or 0
            category = "Debuffs" if name in DEBUFFS else "Utility" if name in UTILITY else "Buffs"
            searchable = f"{name} {self.table.item(row, 3).text()}".casefold()
            visible = (
                (effect_type == "All Effects" or effect_type == category)
                and (not self.missing_only.isChecked() or evidence != "available")
                and (not self.redundant_only.isChecked() or source_count > 1)
                and (not query or query in searchable)
            )
            self.table.setRowHidden(row, not visible)

    def refresh(self):
        load_error = None
        try:
            self.roster = self.build_service.load()
        except Exception as exc:
            self.roster = BuildRoster()
            load_error = f"Could not load saved builds: {exc}"

        build_audits = []
        audit_error = None
        builds = tuple(
            build for build in self.roster.Members
            if (build.Name or "").strip() or (build.Gamertag or "").strip()
            or (build.BuildName or "").strip()
        )
        if builds and DEFAULT_DATABASE.is_file():
            try:
                if self.capability_service is None:
                    self.capability_service = SavedBuildCapabilityService(self.build_service, DEFAULT_DATABASE)
                build_audits = [
                    (build, self.capability_service.audit_build(build))
                    for build in builds
                ]
            except Exception as exc:
                audit_error = f"Saved-build coverage could not be audited: {exc}"
                build_audits = []
        snapshot = summarize_raid_coverage(DEFAULT_RAID_COVERAGE_PROFILE, build_audits)
        self.table.setRowCount(0)
        for effect in CORE_COVERAGE:
            row = self.table.rowCount()
            self.table.insertRow(row)
            names = snapshot.providers[effect]
            conditional = snapshot.conditional_providers[effect]
            state = snapshot.status[effect]
            source_text = ", ".join(names) if names else (
                f"Conditional: {', '.join(conditional)}" if conditional else "—"
            )
            values = [
                effect,
                "Debuff" if effect in DEBUFFS else "Utility" if effect in UTILITY else "Buff",
                "Yes",
                source_text,
                "—",
                "—",
                "—",
                "—",
                {
                    "available": "Available (static)",
                    "conditional": "Conditional",
                    "not_found": "Not identified",
                    "unverified": "Unverified",
                }[state],
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if col == 8:
                    item.setData(Qt.ItemDataRole.UserRole, state)
                if col == 3:
                    item.setData(Qt.ItemDataRole.UserRole, len(names))
                item.setToolTip(
                    "Static build evidence only. Provider assignments and uptime are not inferred."
                    if col >= 3 else "Default raid coverage requirement."
                )
                self.table.setItem(row, col, item)

        self._apply_coverage_filters()
        available = sum(state == "available" for state in snapshot.status.values())
        conditional_count = sum(state == "conditional" for state in snapshot.status.values())
        not_found = sum(state == "not_found" for state in snapshot.status.values())
        unverified = sum(state == "unverified" for state in snapshot.status.values())
        self.summary_card.clear()
        self.summary_card.addWidget(QLabel(
            f"TOTAL EFFECTS   {len(CORE_COVERAGE)}\n"
            f"STATIC SOURCES  {available}\n"
            f"CONDITIONAL     {conditional_count}\n"
            f"NOT IDENTIFIED  {not_found}\n"
            f"UNVERIFIED      {unverified}"
        ))
        self.providers_card.clear()
        provider_counts: dict[str, int] = {}
        for names in snapshot.providers.values():
            for name in names:
                provider_counts[name] = provider_counts.get(name, 0) + 1
        if provider_counts:
            for name, count in sorted(provider_counts.items(), key=lambda x: (-x[1], x[0]))[:5]:
                self.providers_card.addWidget(QLabel(f"{name}   {count} effect(s) identified"))
        else:
            self.providers_card.addWidget(QLabel("No unconditional static sources identified."))
        if load_error or audit_error:
            self.status.warning(load_error or audit_error)
        else:
            self.status.info(f"Coverage evidence • {available}/{len(CORE_COVERAGE)} effects have static sources; uptime unknown.")
