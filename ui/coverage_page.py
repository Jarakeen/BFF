from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from engine.config import DEFAULT_DATABASE, get_data_dir, get_settings_path, get_user_database_path
from models.build_model import BuildRoster, PlayerBuild
from models.raid_plan import RaidPlanCoverageProvider
from services.build_service import BuildService
from services.coverage_pdf_export_service import CoveragePDFRow, export_coverage_pdf
from services.finch_shared_provenance_service import format_shared_timestamp
from services.finch_shared_coverage_service import (
    list_shared_coverage_from_finch,
    publish_coverage_to_finch,
)
from services.saved_build_capability_service import SavedBuildCapabilityService, summarize_raid_coverage
from services.performance_raid_review_runner_service import PerformanceRaidReviewRunnerService
from services.performance_raid_review_selection_mode_service import (
    PerformanceRaidReviewSelectionModeService,
)
from services.raid_coverage_profile import DEFAULT_RAID_COVERAGE_PROFILE
from services.raid_plan_repository import RaidPlanRepository
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar
from ui.foundry_page import FoundryPage
from ui.raid_review_async_task import RaidReviewAsyncTask


_FINCH_COVERAGE_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="finch-coverage")

CORE_COVERAGE = tuple(row.display_name for row in DEFAULT_RAID_COVERAGE_PROFILE.requirements if row.required)
UTILITY = {"Orbs", "Purify"}


class CoveragePage(FoundryPage):
    """Buff/debuff planning desk plus observed Raid Review workspace."""

    def __init__(self, parent=None, raid_review_runner=None):
        super().__init__(parent)
        self.build_service = BuildService(get_data_dir() / "builds.json")
        self.capability_service = None
        self._team_scope: tuple[tuple[str, PlayerBuild], ...] = ()
        self._team_scope_name = ""
        self._team_total_slots = 12
        self.raid_plan_repository = RaidPlanRepository(get_user_database_path())
        self._selected_plan = None
        self.raid_review_runner = raid_review_runner or PerformanceRaidReviewRunnerService()
        self.raid_review_selection_mode_service = PerformanceRaidReviewSelectionModeService()
        self._raid_review_task: RaidReviewAsyncTask | None = None
        self._finch_publish_future: Future | None = None
        self._finch_shared_future: Future | None = None
        self._finch_publish_timer = QTimer(self)
        self._finch_publish_timer.setInterval(100)
        self._finch_publish_timer.timeout.connect(self._poll_finch_publish)
        self._finch_shared_timer = QTimer(self)
        self._finch_shared_timer.setInterval(100)
        self._finch_shared_timer.timeout.connect(self._poll_finch_shared)
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
        self.scope_combo = QComboBox()
        self.scope_combo.addItem("All Saved Builds", "all")
        self.scope_combo.currentIndexChanged.connect(self.refresh)
        self.header.add_context_widget(self._context_field("BUILD SCOPE", self.scope_combo))
        self.publish_finch = QPushButton("To Bff")
        self.publish_finch.setToolTip("Share this Coverage snapshot with the other FoundryDock install through Finch.")
        self.publish_finch.clicked.connect(self._publish_coverage_to_finch)
        self.header.add_context_widget(self.publish_finch)
        self.get_shared_finch = QPushButton("Check Mail")
        self.get_shared_finch.clicked.connect(self._get_shared_coverage_from_finch)
        self.header.add_context_widget(self.get_shared_finch)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._coverage_tab(), "BUFFS & DEBUFFS")
        self.tabs.addTab(self._placeholder("Providers", "Provider reliability and substitutions will live here."), "PROVIDERS")
        self.tabs.addTab(self._raid_review_tab(), "RAID REVIEW")
        self.tabs.addTab(self._placeholder("Encounter Needs", "Encounter-specific required and optional effects will live here."), "ENCOUNTER NEEDS")
        self.tabs.addTab(self._placeholder("Reports", "Coverage exports and historical comparisons will live here."), "REPORTS")
        self.add_workspace(self.tabs)

        self.status = FoundryStatusBar()
        self.set_status(self.status)

    def _selected_raid_plan_id_for_finch(self) -> str:
        data = str(self.scope_combo.currentData() or "").strip()
        return data.split(":", 1)[1].strip() if data.startswith("raid_plan:") else ""

    def _publish_coverage_to_finch(self) -> None:
        plan_id = self._selected_raid_plan_id_for_finch()
        if not plan_id:
            self.status.warning("Select a saved Raid Plan before publishing Coverage.")
            return
        if self._finch_publish_future is not None and not self._finch_publish_future.done():
            self.status.info("Finch Coverage publish is already running.")
            return
        self.publish_finch.setEnabled(False)
        self.status.info("Publishing Coverage to Finch…")
        self._finch_publish_future = _FINCH_COVERAGE_EXECUTOR.submit(
            publish_coverage_to_finch,
            plan_id=plan_id,
            raid_plans_path=get_user_database_path(),
            data_dir=get_data_dir(),
            database_path=DEFAULT_DATABASE,
            settings_path=get_settings_path(),
        )
        self._finch_publish_timer.start()

    def _poll_finch_publish(self) -> None:
        future = self._finch_publish_future
        if future is None or not future.done():
            return
        self._finch_publish_timer.stop()
        self.publish_finch.setEnabled(True)
        self._finch_publish_future = None
        try:
            result = future.result()
        except Exception as exc:
            self.status.warning(f"Finch Coverage publish failed: {type(exc).__name__}: {exc}")
            return
        self.status.success(f"Published Coverage to Finch: {result.snapshot_key}.")

    def _get_shared_coverage_from_finch(self) -> None:
        if self._finch_shared_future is not None and not self._finch_shared_future.done():
            self.status.info("Finch shared Coverage fetch is already running.")
            return
        self.get_shared_finch.setEnabled(False)
        self.status.info("Getting shared Coverage from Finch…")
        self._finch_shared_future = _FINCH_COVERAGE_EXECUTOR.submit(
            list_shared_coverage_from_finch,
            data_dir=get_data_dir(),
            database_path=DEFAULT_DATABASE,
            settings_path=get_settings_path(),
        )
        self._finch_shared_timer.start()

    def _poll_finch_shared(self) -> None:
        future = self._finch_shared_future
        if future is None or not future.done():
            return
        self._finch_shared_timer.stop()
        self.get_shared_finch.setEnabled(True)
        self._finch_shared_future = None
        try:
            previews = tuple(future.result())
        except Exception as exc:
            self.status.warning(f"Finch shared Coverage fetch failed: {type(exc).__name__}: {exc}")
            return
        if not previews:
            self.status.info("Finch has no shared Coverage snapshots.")
            return

        labels = [
            f"{row.name or row.plan_id} • {row.trial_id or 'Trial unknown'} • "
            f"{row.covered}/{row.total_effects} covered • "
            f"{row.published_by or 'Unknown publisher'} • "
            f"{format_shared_timestamp(row.updated_at)}"
            for row in previews
        ]
        selected, accepted = QInputDialog.getItem(
            self, "Shared Coverage on Finch", "View shared Coverage snapshot:", labels, 0, False
        )
        if not accepted:
            self.status.info("Shared Coverage view cancelled.")
            return
        try:
            row = previews[labels.index(selected)]
        except (ValueError, IndexError):
            self.status.warning("The selected shared Coverage snapshot is unavailable.")
            return

        problem_rows = [
            effect for effect in row.effects
            if effect.coverage_state == "missing" or effect.needs_attention
        ]
        details = []
        for effect in problem_rows[:8]:
            providers = effect.primary or effect.static_providers or effect.conditional_providers
            provider_text = ", ".join(providers) if providers else "No provider"
            details.append(f"• {effect.effect_name}: {effect.label} • {provider_text}")
        if len(problem_rows) > 8:
            details.append(f"• +{len(problem_rows) - 8} more review item(s)")

        QMessageBox.information(
            self,
            "Shared Coverage",
            (
                f"{row.name or row.plan_id}\n"
                f"Trial: {row.trial_id or 'Unknown'}\n"
                f"Team: {row.team_name or 'Not set'}\n"
                f"Published by: {row.published_by or 'Unknown'}\n"
                f"Updated: {format_shared_timestamp(row.updated_at)}\n\n"
                f"Covered: {row.covered}/{row.total_effects}\n"
                f"Missing: {row.missing}\n"
                f"Needs attention: {row.needs_attention}\n"
                f"Duplicate primary: {row.duplicate_primary}\n"
                f"Unresolved chairs: {row.unresolved_chairs}\n\n"
                + ("Review items:\n" + "\n".join(details) + "\n\n" if details else "")
                + "This is a read-only Finch snapshot. Local Coverage was not changed."
            ),
        )
        self.status.info(f"Viewed shared Coverage for {row.name or row.plan_id}; local state unchanged.")

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

        self.scope_card = FoundryCard("Who Is In This Check", "team")
        self.scope_note = QLabel()
        self.scope_note.setWordWrap(True)
        self.scope_card.addWidget(self.scope_note)
        root.addWidget(self.scope_card)

        filters = QHBoxLayout()
        self.effect_filter = QComboBox()
        self.effect_filter.addItems(["All Effects", "Buffs", "Debuffs", "Utility"])
        self.missing_only = QCheckBox("Needs Review Only")
        self.redundant_only = QCheckBox("Multiple Static Sources")
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search effect...")
        self.remove_provider_button = QPushButton("Remove Provider")
        self.remove_provider_button.clicked.connect(self._remove_manual_provider)
        filters.addWidget(self.effect_filter)
        filters.addWidget(self.remove_provider_button)
        filters.addWidget(self.missing_only)
        filters.addWidget(self.redundant_only)
        filters.addStretch(1)
        filters.addWidget(self.search, 1)
        self.effect_filter.currentTextChanged.connect(self._apply_coverage_filters)
        self.missing_only.toggled.connect(self._apply_coverage_filters)
        self.redundant_only.toggled.connect(self._apply_coverage_filters)
        self.search.textChanged.connect(self._apply_coverage_filters)

        table_card = FoundryCard("Saved-Build Coverage Evidence", "◈")
        self.add_provider_button = QPushButton("Add Provider")
        self.add_provider_button.setToolTip("Mark the selected effect covered by raid-lead assignment. Provider and source are required.")
        self.add_provider_button.clicked.connect(self._add_manual_provider)
        self.save_coverage_button = QPushButton("Save Coverage")
        self.save_coverage_button.setProperty("primary", True)
        self.save_coverage_button.setToolTip(
            "Verify the selected Raid Plan's Coverage assignments are persisted in the canonical Raid Plan."
        )
        self.save_coverage_button.clicked.connect(self._save_coverage)
        self.export_coverage_pdf_button = QPushButton("Export PDF")
        self.export_coverage_pdf_button.setToolTip(
            "Export the selected Raid Plan's covered effects, providers, sources, backups, and Coverage status."
        )
        self.export_coverage_pdf_button.clicked.connect(self._export_coverage_pdf)
        header_actions = QWidget()
        header_actions_layout = QHBoxLayout(header_actions)
        header_actions_layout.setContentsMargins(0, 0, 0, 0)
        header_actions_layout.setSpacing(6)
        header_actions_layout.addWidget(self.add_provider_button)
        header_actions_layout.addWidget(self.export_coverage_pdf_button)
        header_actions_layout.addWidget(self.save_coverage_button)
        table_card.set_header_action(header_actions)
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
        self.table.itemDoubleClicked.connect(lambda *_args: self._add_manual_provider())
        table_card.addWidget(self.table)
        root.addWidget(table_card, 4)

        lower = QHBoxLayout()
        lower.setSpacing(8)
        self.summary_card = FoundryCard("Coverage Summary", "✓").set_watermark("compass", 0.055)
        self.providers_card = FoundryCard("Identified Static Sources", "♜").set_watermark("compass", 0.045)
        notes = FoundryCard("Coverage Notes", "✎").make_parchment().set_watermark("feather", 0.11)
        notes.set_body_margins(12, 3, 12, 10)
        self.coverage_notes_label = QLabel(
            "• This fixed watch list shows only canonically resolved saved-build effects.\n"
            "• Static availability does not assign a player or prove uptime.\n"
            "• Review conditional and unverified effects before planning a pull."
        )
        self.coverage_notes_label.setProperty("coverageNotesBody", True)
        self.coverage_notes_label.setWordWrap(True)
        self.coverage_notes_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        notes.addWidget(self.coverage_notes_label)
        notes.addStretch(1)
        lower.addWidget(self.summary_card, 2)
        lower.addWidget(self.providers_card, 2)
        lower.addWidget(notes, 2)
        root.addLayout(lower, 1)
        return page

    def _export_coverage_pdf(self, *_args) -> None:
        plan_id = self._selected_raid_plan_id_for_finch()
        if not plan_id:
            self.status.warning("Select a saved Raid Plan before exporting Coverage.")
            return

        try:
            plan = self.raid_plan_repository.get(plan_id)
        except Exception as exc:
            self.status.error(f"Could not load Raid Plan for Coverage export: {exc}")
            return
        if plan is None:
            self.status.warning("Selected Raid Plan is no longer available.")
            return

        manual_sources_by_effect: dict[str, list[str]] = {}
        for provider in tuple(getattr(plan, "coverage_providers", ()) or ()):
            detail = str(provider.source or "").strip()
            note = str(provider.note or "").strip()
            if note:
                detail = f"{detail} — {note}"
            if detail:
                manual_sources_by_effect.setdefault(
                    str(provider.effect_name or "").strip().casefold(),
                    [],
                ).append(detail)

        covered_states = {
            "assigned_manual",
            "assigned_supported",
            "assigned_conditional",
            "assigned_unproven",
            "backup_only",
            "unassigned_available",
            "available",
            "conditional",
        }
        rows: list[CoveragePDFRow] = []
        for row_index in range(self.table.rowCount()):
            evidence_item = self.table.item(row_index, 8)
            state = (
                str(evidence_item.data(Qt.ItemDataRole.UserRole) or "").strip()
                if evidence_item is not None
                else ""
            )
            if state not in covered_states:
                continue

            def cell(column: int) -> str:
                item = self.table.item(row_index, column)
                return str(item.text() if item is not None else "").strip()

            effect = cell(0)
            table_source = cell(3)
            manual_sources = tuple(
                dict.fromkeys(
                    manual_sources_by_effect.get(effect.casefold(), ())
                )
            )
            source = (
                "Raid lead: " + " | ".join(manual_sources)
                if manual_sources
                else table_source
            )
            if manual_sources and table_source and table_source != "—":
                source += f" • Evidence: {table_source}"

            rows.append(
                CoveragePDFRow(
                    effect=effect,
                    provider=cell(4),
                    backup=cell(5),
                    source=source,
                    status=cell(8),
                )
            )

        safe_name = "".join(
            char if char.isalnum() or char in {" ", "-", "_"} else "_"
            for char in str(plan.name or "Raid Plan")
        ).strip() or "Raid Plan"
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Coverage PDF",
            f"{safe_name}_coverage.pdf",
            "Printer-Friendly PDF (*.pdf)",
        )
        if not filename:
            return
        path = Path(filename)
        if path.suffix.casefold() != ".pdf":
            path = path.with_suffix(".pdf")

        try:
            export_coverage_pdf(plan, tuple(rows), path)
        except Exception as exc:
            self.status.error(f"Coverage PDF export failed: {exc}")
            return
        self.status.success(
            f"Exported {len(rows)} covered effect(s) to {path}."
        )

    def set_team_scope(
        self, name: str, members: tuple[tuple[str, PlayerBuild], ...], *, total_slots: int = 12
    ) -> None:
        """Compatibility boundary: Coverage no longer exposes transient team scopes."""
        del name, members, total_slots
        self.status.warning(
            "Coverage evaluates saved Raid Plans only. Save the team as a trial-specific "
            "Raid Plan, then select that plan here."
        )

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

    def _selected_plan_id(self) -> str:
        data = str(self.scope_combo.currentData() or "").strip()
        return data.split(":", 1)[1].strip() if data.startswith("raid_plan:") else ""

    def _selected_effect_name(self) -> str:
        row = self.table.currentRow()
        item = self.table.item(row, 0) if row >= 0 else None
        return item.text().strip() if item is not None else ""

    def _add_manual_provider(self) -> None:
        plan_id = self._selected_plan_id()
        effect = self._selected_effect_name()
        if not plan_id:
            self.status.warning("Select a saved Raid Plan before assigning manual Coverage.")
            return
        if not effect:
            self.status.warning("Select a Coverage effect first.")
            return
        plan = self.raid_plan_repository.get(plan_id)
        if plan is None:
            self.status.warning("That Raid Plan is no longer available. Refresh Coverage.")
            return
        members = tuple(plan.members)
        if not members:
            self.status.warning("This Raid Plan has no seats to assign as a provider.")
            return
        labels = [
            f"{member.seat_id} • {member.character_name or member.gamertag or 'Open'}"
            for member in members
        ]
        selected, ok = QInputDialog.getItem(self, f"Cover {effect}", "Provider / seat:", labels, 0, False)
        if not ok:
            return
        member = members[labels.index(selected)]
        source, ok = QInputDialog.getText(
            self, f"Cover {effect}",
            "Why is this covered? Enter the skill, set, passive, or other source:",
        )
        source = source.strip()
        if not ok or not source:
            if ok:
                self.status.warning("Coverage needs a source. Even vibes must be documented.")
            return
        note, ok = QInputDialog.getText(
            self, f"Cover {effect}",
            "Optional note / explanation:",
        )
        if not ok:
            return
        updated = plan.with_coverage_provider(
            RaidPlanCoverageProvider(
                effect_name=effect,
                seat_id=member.seat_id,
                source=source,
                note=note.strip() or None,
            )
        )
        try:
            self.raid_plan_repository.save(updated, expected=plan)
            persisted = self.raid_plan_repository.get(plan_id)
            expected_provider = next(
                (
                    row for row in (persisted.coverage_for(effect) if persisted is not None else ())
                    if row.seat_id.casefold() == member.seat_id.casefold()
                    and row.source == source
                    and (row.note or "") == (note.strip() or "")
                ),
                None,
            )
            if expected_provider is None:
                raise RuntimeError("saved provider failed Coverage read-back verification")
        except Exception as exc:
            self.status.error(f"Could not save manual Coverage: {exc}")
            return
        self._coverage_selected_plan_id = plan_id
        self.status.success(f"{effect} marked covered by {member.character_name or member.gamertag or member.seat_id} • {source}.")
        self.refresh()

    def _save_coverage(self) -> None:
        plan_id = self._selected_plan_id()
        if not plan_id:
            QMessageBox.warning(self, "Save Coverage", "Select a saved Raid Plan before saving Coverage.")
            self.status.warning("Select a saved Raid Plan before saving Coverage.")
            return
        plan = self.raid_plan_repository.get(plan_id)
        if plan is None:
            QMessageBox.critical(self, "Save Coverage", "Selected Raid Plan is no longer available. Coverage was not saved.")
            self.status.error("Selected Raid Plan is no longer available; Coverage was not saved.")
            return

        self.save_coverage_button.setEnabled(False)
        self.save_coverage_button.setText("Saving…")
        self.status.info(f"Saving Coverage for {plan.name}…")
        try:
            # Manual provider edits are persisted at edit time. This explicit Save
            # is a durable checkpoint: rewrite the complete Pydantic-validated Raid
            # Plan snapshot, then prove the exact Coverage payload survived read-back.
            expected_providers = tuple(plan.coverage_providers)
            saved = self.raid_plan_repository.save(plan, expected=plan)
            persisted = self.raid_plan_repository.get(plan_id)
            if persisted is None:
                raise RuntimeError("saved Raid Plan failed Coverage read-back verification")
            if tuple(saved.coverage_providers) != expected_providers:
                raise RuntimeError("saved Coverage payload differs from the requested checkpoint")
            if tuple(persisted.coverage_providers) != expected_providers:
                raise RuntimeError("Coverage providers changed during persistence verification")
        except Exception as exc:
            self.save_coverage_button.setEnabled(True)
            self.save_coverage_button.setText("Save Coverage")
            QMessageBox.critical(self, "Coverage Save Failed", str(exc))
            self.status.error(f"Could not save Coverage: {exc}")
            return

        self._coverage_selected_plan_id = plan_id
        count = len(persisted.coverage_providers)
        self.save_coverage_button.setEnabled(True)
        self.save_coverage_button.setText("Saved ✓")
        QTimer.singleShot(1800, lambda: self.save_coverage_button.setText("Save Coverage"))
        message = (
            f"Coverage saved and verified for {persisted.name}. "
            f"{count} manual provider" + ("" if count == 1 else "s") + " persisted."
        )
        QMessageBox.information(self, "Coverage Saved", message)
        self.status.success(message)
        self.refresh()

    def _remove_manual_provider(self) -> None:
        plan_id = self._selected_plan_id()
        effect = self._selected_effect_name()
        plan = self.raid_plan_repository.get(plan_id) if plan_id else None
        if plan is None or not effect:
            return
        rows = plan.coverage_for(effect)
        if not rows:
            self.status.info(f"{effect} has no raid-lead Coverage assignment to remove.")
            return
        labels = []
        for provider in rows:
            member = plan.member(provider.seat_id)
            who = (member.character_name or member.gamertag) if member else provider.seat_id
            labels.append(f"{provider.seat_id} • {who} • {provider.source}")
        selected, ok = QInputDialog.getItem(self, f"Remove {effect} Provider", "Manual provider:", labels, 0, False)
        if not ok:
            return
        provider = rows[labels.index(selected)]
        updated = plan.without_coverage_provider(effect, provider.seat_id)
        try:
            self.raid_plan_repository.save(updated, expected=plan)
            persisted = self.raid_plan_repository.get(plan_id)
            if persisted is None:
                raise RuntimeError("saved Raid Plan failed Coverage read-back verification")
            if any(
                row.seat_id.casefold() == provider.seat_id.casefold()
                for row in persisted.coverage_for(effect)
            ):
                raise RuntimeError("removed provider survived Coverage read-back verification")
        except Exception as exc:
            self.status.error(f"Could not remove manual Coverage: {exc}")
            return
        self._coverage_selected_plan_id = plan_id
        self.status.success(f"Removed raid-lead Coverage assignment for {effect}.")
        self.refresh()

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
            type_item = self.table.item(row, 1)
            type_text = str(type_item.text() if type_item is not None else "").strip()
            category = (
                "Utility"
                if name in UTILITY
                else "Debuffs"
                if "debuff" in type_text.casefold()
                else "Buffs"
            )
            searchable = f"{name} {self.table.item(row, 3).text()}".casefold()
            visible = (
                (effect_type == "All Effects" or effect_type == category)
                and (
                    not self.missing_only.isChecked()
                    or evidence not in {"available", "assigned_supported"}
                )
                and (not self.redundant_only.isChecked() or source_count > 1)
                and (not query or query in searchable)
            )
            self.table.setRowHidden(row, not visible)

    def snapshot_for_builds(self, builds: tuple[PlayerBuild, ...]):
        """Audit an explicit build subset without claiming those builds form an assigned provider plan."""
        self._last_audit_error = None
        empty = summarize_raid_coverage(DEFAULT_RAID_COVERAGE_PROFILE, [])
        if not builds or not DEFAULT_DATABASE.is_file():
            return empty
        try:
            if self.capability_service is None:
                self.capability_service = SavedBuildCapabilityService(self.build_service, DEFAULT_DATABASE)
            audits = [(build, self.capability_service.audit_build(build)) for build in builds]
        except Exception as exc:
            self._last_audit_error = f"Saved-build coverage could not be audited: {exc}"
            self.status.warning(self._last_audit_error)
            return empty
        return summarize_raid_coverage(DEFAULT_RAID_COVERAGE_PROFILE, audits)

    def refresh(self):
        load_error = None
        try:
            self.roster = self.build_service.load()
        except Exception as exc:
            self.roster = BuildRoster()
            load_error = f"Could not load saved builds: {exc}"

        saved_builds = tuple(
            build for build in self.roster.Members
            if (build.Name or "").strip() or (build.Gamertag or "").strip()
            or (build.BuildName or "").strip()
        )
        team_active = self.scope_combo.currentData() == "team" and bool(self._team_scope)
        builds = tuple(build for _, build in self._team_scope) if team_active else saved_builds
        if team_active:
            members = ", ".join(
                f"{slot}: {build.Name or build.Gamertag or build.BuildName} ({build.BuildName or 'Saved Build'})"
                for slot, build in self._team_scope
            )
            self.scope_card.set_title(f"Selected Team: {self._team_scope_name}")
            self.scope_note.setText(
                f"{len(self._team_scope)}/{self._team_total_slots} slots with saved builds • {members}\n"
                "Team Optimization snapshot. Resend after edits. Static effects only; provider duties and uptime remain unassigned."
            )
        else:
            self.scope_card.set_title("All Saved Builds")
            self.scope_note.setText(
                f"Checking all {len(saved_builds)} named saved builds, regardless of raid team. "
                "To check one team, select its builds in Team Optimization, then use Send Team to Coverage on Raid Engine."
            )
        plan_id = self._selected_plan_id()
        self._selected_plan = self.raid_plan_repository.get(plan_id) if plan_id else None
        snapshot = self.snapshot_for_builds(builds)
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
            manual_rows = self._selected_plan.coverage_for(effect) if self._selected_plan is not None else ()
            manual_labels = []
            for provider in manual_rows:
                member = self._selected_plan.member(provider.seat_id)
                who = (member.character_name or member.gamertag) if member else provider.seat_id
                detail = f"{who} • {provider.source}"
                if provider.note:
                    detail += f" • {provider.note}"
                manual_labels.append(detail)
            manual_text = "; ".join(manual_labels)
            values = [
                effect,
                "Debuff" if effect in DEBUFFS else "Utility" if effect in UTILITY else "Buff",
                "Yes",
                source_text,
                manual_text or "—",
                "—",
                "—",
                "—",
                ("Raid Lead Assigned ◇" if manual_rows else {
                    "available": "Available (static)",
                    "conditional": "Conditional",
                    "not_found": "Not identified",
                    "unverified": "Unverified",
                }[state]),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if col == 8:
                    item.setData(Qt.ItemDataRole.UserRole, "manual" if manual_rows else state)
                if col == 3:
                    item.setData(Qt.ItemDataRole.UserRole, len(names))
                item.setToolTip(
                    ("Raid lead assigned coverage. This counts as planned coverage but remains distinct from Build-confirmed evidence." if manual_rows and col in {4, 8} else "Static build evidence only. Provider assignments and uptime are not inferred.")
                    if col >= 3 else "Default raid coverage requirement."
                )
                self.table.setItem(row, col, item)

        self._apply_coverage_filters()
        manual_covered = sum(bool(self._selected_plan and self._selected_plan.coverage_for(effect)) for effect in CORE_COVERAGE)
        available = sum(state == "available" for state in snapshot.status.values())
        conditional_count = sum(state == "conditional" for state in snapshot.status.values())
        not_found = sum(state == "not_found" for state in snapshot.status.values())
        unverified = sum(state == "unverified" for state in snapshot.status.values())
        self.summary_card.clear()
        self.summary_card.addWidget(QLabel(
            f"TOTAL EFFECTS   {len(CORE_COVERAGE)}\n"
            f"STATIC SOURCES  {available}\n"
            f"RAID LEAD ASSIGNED  {manual_covered}\n"
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
        if load_error or self._last_audit_error:
            self.status.warning(load_error or self._last_audit_error)
        else:
            self.status.info(f"Coverage evidence • {available}/{len(CORE_COVERAGE)} effects have static sources; uptime unknown.")
