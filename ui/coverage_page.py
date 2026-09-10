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

from engine.config import get_data_dir
from models.build_model import BuildRoster, PlayerBuild
from services.build_service import BuildService
from services.performance_raid_review_lokkestiiz_runner_service import (
    PerformanceRaidReviewLokkestiizRunnerService,
)
from services.raid_coverage_profile import DEFAULT_RAID_COVERAGE_PROFILE
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar
from ui.foundry_page import FoundryPage
from ui.raid_review_async_task import RaidReviewAsyncTask


CORE_COVERAGE = tuple(
    row.display_name
    for row in DEFAULT_RAID_COVERAGE_PROFILE.requirements
    if row.required
)

ALIASES = {
    "War Horn": ("war horn", "aggressive horn"),
    "Orbs": ("orb", "necrotic orb", "energy orb", "shards"),
    "Crusher": ("crusher", "crushing"),
    "Minor Brittle": ("minor brittle", "brittle"),
    "Magickasteal": ("magickasteal", "magicka steal"),
    "Purify": ("purify", "purifying"),
}


class CoveragePage(FoundryPage):
    """Buff/debuff planning desk plus observed Raid Review workspace."""

    def __init__(self, parent=None, raid_review_runner=None):
        super().__init__(parent)
        self.build_service = BuildService(get_data_dir() / "builds.json")
        self.raid_review_runner = (
            raid_review_runner or PerformanceRaidReviewLokkestiizRunnerService()
        )
        self._raid_review_task: RaidReviewAsyncTask | None = None
        self.roster = BuildRoster()
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        self.header = FoundryHeader(
            title="Coverage & Buff Management",
            subtitle="Plan encounter coverage, then review what actually happened in combat.",
            department="Raid Engine • Coverage",
        )
        self.set_header(self.header)

        self.encounter_combo = QComboBox()
        self.encounter_combo.addItems(["Current Encounter", "Whole Trial", "Custom Plan"])
        self.header.add_context_widget(self._context_field("VIEW", self.encounter_combo))

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
        self.missing_only = QCheckBox("Show Missing Only")
        self.redundant_only = QCheckBox("Show Redundant")
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search effect...")
        filters.addWidget(self.effect_filter)
        filters.addWidget(self.missing_only)
        filters.addWidget(self.redundant_only)
        filters.addStretch(1)
        filters.addWidget(self.search, 1)

        table_card = FoundryCard("Coverage Plan", "◈")
        table_card.set_header_action(QPushButton("Edit Requirements"))
        table_card.addLayout(filters)
        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels([
            "Effect", "Type", "Required", "Source", "Planned Provider",
            "Backup", "Target Uptime", "Actual Uptime", "Status",
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
        self.providers_card = FoundryCard("Most Reliable Providers", "♜").set_watermark("compass", 0.045)
        notes = FoundryCard("Coverage Notes", "✎").make_parchment().set_watermark("feather", 0.11)
        notes.addWidget(QLabel(
            "• Encounter requirements can override the default watch list.\n"
            "• Planned provider is not the same thing as measured uptime.\n"
            "• Decide who owns each required effect before the pull."
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
        self.raid_review_report_input = QLineEdit()
        self.raid_review_report_input.setPlaceholderText("ESO Logs report code or report URL")
        self.raid_review_load_fights_button = QPushButton("Load Fights")
        self.raid_review_load_fights_button.clicked.connect(self._load_raid_review_fights)
        self.raid_review_run_button = QPushButton("Run Raid Review")
        self.raid_review_run_button.setProperty("primary", True)
        self.raid_review_run_button.setEnabled(False)
        self.raid_review_run_button.setToolTip(
            "Query the checked Lokkestiiz fights directly from ESO Logs and compare them as one Raid Review."
        )
        self.raid_review_run_button.clicked.connect(self._run_raid_review)
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
        intake.addWidget(self.raid_review_fights_table)
        intake.addWidget(QLabel(
            "Load the report, check the Lokkestiiz pulls you want compared, then run the review. "
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

    def _set_raid_review_busy(self, busy: bool) -> None:
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
        report_code = self.raid_review_report_input.text().strip()
        if not report_code:
            self.status.warning("Enter an ESO Logs report code or report URL first.")
            return

        self.raid_review_fights_table.setRowCount(0)
        self.status.info("Loading Lokkestiiz pulls from ESO Logs...")
        self._start_raid_review_task(
            lambda: self.raid_review_runner.list_lokkestiiz_fights(report_code),
            self._raid_review_fights_loaded,
            "Could not load Raid Review fights",
        )

    def _raid_review_fights_loaded(self, choices) -> None:
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

        if choices:
            self.status.success(f"Loaded {len(choices)} Lokkestiiz pull(s). Uncheck any pulls you do not want compared.")
        else:
            self.status.warning("No Lokkestiiz pulls were found in that report.")

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
        report_code = self.raid_review_report_input.text().strip()
        if not report_code:
            self.status.warning("Enter an ESO Logs report code or report URL first.")
            return

        fight_ids = self._selected_raid_review_fight_ids()
        if not fight_ids:
            self.status.warning("Check at least one Lokkestiiz pull before running Raid Review.")
            return

        self.status.info(
            f"Running Raid Review for {len(fight_ids)} selected Lokkestiiz pull(s) from ESO Logs..."
        )
        self._start_raid_review_task(
            lambda: self.raid_review_runner.review_report(report_code, fight_ids),
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

    @staticmethod
    def _build_text(build: PlayerBuild) -> str:
        values = list(build.FrontBarSkills) + list(build.BackBarSkills)
        values.extend([
            build.FrontBarWeapon.Set, build.BackBarWeapon.Set,
            *[entry.get("Set", "") for entry in build.Armor.values()],
        ])
        return " ".join(str(value or "") for value in values).lower()

    def _resolve(self):
        providers = {name: [] for name in CORE_COVERAGE}
        for member in self.roster.Members:
            text = self._build_text(member)
            provider = member.Name or member.Gamertag or member.BuildName or "Unnamed"
            for effect in CORE_COVERAGE:
                aliases = ALIASES.get(effect, (effect.lower(),))
                if any(alias in text for alias in aliases):
                    providers[effect].append(provider)
        return providers

    def refresh(self):
        try:
            self.roster = self.build_service.load()
        except Exception as exc:
            self.roster = BuildRoster()
            self.status.warning(f"Could not load saved builds: {exc}")

        providers = self._resolve()
        self.table.setRowCount(0)
        source_defaults = {
            "Major Courage": "SPC / class", "Major Vulnerability": "Colossus / sets",
            "Major Breach": "taunt / skill", "Crusher": "weapon enchant",
            "Minor Brittle": "frost source", "Orbs": "healer skill",
            "War Horn": "ultimate", "Purify": "cleanse",
        }
        for effect in CORE_COVERAGE:
            row = self.table.rowCount()
            self.table.insertRow(row)
            names = providers[effect]
            status = "Covered" if names else "Missing"
            values = [
                effect,
                "Debuff" if effect in {"Major Vulnerability", "Major Breach", "Crusher", "Minor Brittle", "Minor Maim"} else "Buff / Utility",
                "Yes",
                source_defaults.get(effect, "skill / gear"),
                names[0] if names else "—",
                names[1] if len(names) > 1 else "—",
                "High",
                "—",
                status,
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if col == 8:
                    item.setData(Qt.ItemDataRole.UserRole, status)
                self.table.setItem(row, col, item)

        missing = sum(1 for effect in CORE_COVERAGE if not providers[effect])
        covered = len(CORE_COVERAGE) - missing
        overlap = sum(1 for effect in CORE_COVERAGE if len(providers[effect]) > 1)
        self.summary_card.clear()
        self.summary_card.addWidget(QLabel(
            f"TOTAL EFFECTS   {len(CORE_COVERAGE)}\n"
            f"FULLY COVERED   {covered}\n"
            f"MISSING         {missing}\n"
            f"OVERLAP         {overlap}"
        ))
        self.providers_card.clear()
        provider_counts: dict[str, int] = {}
        for names in providers.values():
            for name in names:
                provider_counts[name] = provider_counts.get(name, 0) + 1
        if provider_counts:
            for name, count in sorted(provider_counts.items(), key=lambda x: (-x[1], x[0]))[:5]:
                self.providers_card.addWidget(QLabel(f"✓  {name}   {count} effect(s)"))
        else:
            self.providers_card.addWidget(QLabel("No providers resolved from saved build names yet."))
        self.status.info(f"Coverage plan ready • {covered}/{len(CORE_COVERAGE)} watch-list effects represented.")
