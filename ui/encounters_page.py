# ==================================================
# Black Feather Foundry
#
# File:
# ui/encounters_page.py
#
# Purpose:
# Raid Engine encounter planning workspace.
# ==================================================

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QInputDialog,
    QTabWidget,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from engine.config import get_data_dir
from services.encounter_boss_guide import EncounterBossGuideService
from services.encounter_raid_map_store import EncounterRaidMapStore
from services.expedition_service import ExpeditionService
from services.finch_raid_map_publish_service import publish_raid_map_and_plan_to_finch
from services.raid_plan_repository import RaidPlanRepository
from services.raid_section_state_service import RaidSectionStateService
from ui.components.encounter_board import EncounterBoard
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar
from ui.foundry_page import FoundryPage


_FINCH_RAID_MAP_EXECUTOR = ThreadPoolExecutor(
    max_workers=1,
    thread_name_prefix="finch-raid-map",
)


class EncountersPage(FoundryPage):
    """Encounter positioning, timelines, mechanics, and assignments."""

    def __init__(
        self,
        expedition: ExpeditionService,
        guide_service: EncounterBossGuideService | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.expedition = expedition
        self.guide_service = guide_service or EncounterBossGuideService(
            get_data_dir() / "eso.db"
        )
        self._guide_summaries = ()
        self._finch_raid_map_future: Future | None = None
        self._finch_raid_map_timer = QTimer(self)
        self._finch_raid_map_timer.setInterval(100)
        self._finch_raid_map_timer.timeout.connect(self._poll_finch_raid_map_publish)
        self.raid_plan_repository = RaidPlanRepository(get_data_dir() / "raid_plans.json")
        self.raid_map_store = EncounterRaidMapStore(get_data_dir())
        self.raid_section_state = RaidSectionStateService()
        self._build_ui()
        self._connect_boss_selector()
        self.refresh_context()

    @staticmethod
    def _placeholder(text: str, *, centered: bool = False) -> QLabel:
        label = QLabel(text)
        label.setWordWrap(True)
        label.setProperty("muted", True)
        if centered:
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return label

    @staticmethod
    def _context_box(title: str, value: QLabel) -> QWidget:
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        caption = QLabel(title)
        caption.setProperty("sidebarHeading", True)
        layout.addWidget(caption)
        layout.addWidget(value)
        return box

    def _build_ui(self):
        self.header = FoundryHeader(
            title="Encounters",
            subtitle="Position the team. Track the phase. Keep the plan legible.",
            department="Raid Engine • Encounters",
            icon="trial",
        )
        self.set_header(self.header)

        self.active_trial = QLabel("No Active Expedition")
        self.group_size = QLabel("— / —")
        directive = QLabel("Tonight's Directive\nExecution matters. Stay calm. Stay together.")
        directive.setWordWrap(True)
        directive.setProperty("parchment", True)

        self.header.add_context_widget(self._context_box("ACTIVE TRIAL", self.active_trial))
        self.raid_plan_combo = QComboBox()
        self.raid_plan_combo.setMinimumWidth(230)
        self.raid_plan_combo.setToolTip(
            "Optional Raid Plan context for this encounter map. Leave None for a general map."
        )
        self.raid_plan_combo.currentIndexChanged.connect(self._raid_plan_context_changed)
        self.header.add_context_widget(self._context_box("RAID PLAN", self.raid_plan_combo))
        self.header.add_context_widget(self._context_box("GROUP SIZE", self.group_size))
        self.header.add_context_widget(directive)

        workspace = QWidget()
        root = QVBoxLayout(workspace)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        self.section_tabs = QTabWidget()
        self.section_tabs.addTab(self._overview_tab(), "OVERVIEW")
        self.section_tabs.addTab(self._assignments_tab(), "ASSIGNMENTS")
        self.section_tabs.addTab(self._mechanics_tab(), "MECHANICS")
        self.section_tabs.addTab(self._empty_section("Loot, rewards, and achievement targets will appear here."), "LOOT & REWARDS")
        self.section_tabs.addTab(self._empty_section("Encounter notes will appear here."), "NOTES")
        self.section_tabs.setCurrentIndex(1)
        root.addWidget(self.section_tabs, 1)

        self.add_workspace(workspace)

        self.status = FoundryStatusBar()
        self.status.info("Encounter workspace ready. Mechanics includes the interactive positioning board.")
        self.set_status(self.status)

    def _overview_tab(self) -> QWidget:
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        summary = FoundryCard("Encounter Overview", "trial").set_watermark("compass", 0.04)
        summary.addWidget(self._placeholder("Trial summary, selected boss, progression state, and encounter notes."))
        layout.addWidget(summary, 2)

        progression = FoundryCard("Progression", "progression")
        progression.addWidget(self._placeholder("Best pull\nPull count\nCurrent phase\nRecent result"))
        layout.addWidget(progression, 1)

        raid_notes = FoundryCard("Raid Lead Notes", "feather").make_parchment().set_watermark("feather", 0.10)
        raid_notes.addWidget(self._placeholder("High-level direction for tonight's work."))
        layout.addWidget(raid_notes, 1)
        return tab

    def _assignments_tab(self) -> QWidget:
        tab = QWidget()
        root = QVBoxLayout(tab)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        upper = QHBoxLayout()
        upper.setSpacing(8)

        left = QVBoxLayout()
        left.setSpacing(8)

        controls = FoundryCard("Select Boss", "boss")
        boss_row = QHBoxLayout()
        self.boss_combo = QComboBox()
        boss_row.addWidget(self.boss_combo, 1)
        self.previous_boss_button = QPushButton("‹")
        self.next_boss_button = QPushButton("›")
        boss_row.addWidget(self.previous_boss_button)
        boss_row.addWidget(self.next_boss_button)
        controls.addLayout(boss_row)

        phase_row = QHBoxLayout()
        phase_list = QListWidget()
        phase_list.addItems(("Phase 1   0:00 – 2:10", "Phase 2   2:10 – 4:20", "Phase 3   4:20 – 6:10", "Execute   6:10+"))
        phase_list.setMaximumWidth(180)
        phase_row.addWidget(phase_list)

        self.positioning_card = FoundryCard("Positioning", "treasure-map").set_watermark("compass", 0.035)
        from ui.components.field_office_empty_artwork import FieldOfficeEmptyArtwork

        self.positioning_preview = FieldOfficeEmptyArtwork(
            "unrecorded_raid_map.webp",
            "No positioning capture yet.\nBuild the encounter on the Mechanics tab, then Capture Positioning.",
        )
        self.positioning_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.positioning_preview.setMinimumHeight(300)
        self.positioning_preview.setProperty("positioningMap", True)
        self.positioning_preview.setText(
            "No positioning capture yet.\n\n"
            "Build the encounter on the Mechanics tab, then use Capture Positioning."
        )
        self.positioning_card.addWidget(self.positioning_preview)
        open_board = QPushButton("Open Mechanics Map")
        open_board.clicked.connect(lambda: self.section_tabs.setCurrentIndex(2))
        self.positioning_card.set_header_action(open_board)
        phase_row.addWidget(self.positioning_card, 1)
        controls.addLayout(phase_row)
        left.addWidget(controls, 3)

        assignments = FoundryCard("Player Assignments (Phase 1)", "assignment")
        filter_row = QHBoxLayout()
        for text in ("All Players", "Tanks", "Healers", "DPS", "Special"):
            button = QPushButton(text)
            button.setCheckable(True)
            filter_row.addWidget(button)
        search = QLineEdit()
        search.setPlaceholderText("Search player or assignment…")
        filter_row.addWidget(search, 1)
        assignments.addLayout(filter_row)

        table = QTableWidget(0, 5)
        table.setHorizontalHeaderLabels(("Player", "Role", "Primary Assignment", "Secondary Assignment(s)", "Notes"))
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setMinimumHeight(230)
        assignments.addWidget(table)
        left.addWidget(assignments, 2)
        upper.addLayout(left, 6)

        middle = QVBoxLayout()
        middle.setSpacing(8)

        timeline = FoundryCard("Phase Timeline Overview", "stopwatch")
        timeline.addWidget(self._placeholder(
            "0:00   Pull\n"
            "0:20   Portal Spawn\n"
            "0:45   Heavy Attack\n"
            "1:10   Orbs\n"
            "1:30   Portal Adds\n"
            "1:55   Chains\n"
            "2:10   Phase Transition\n"
            "4:20   Phase 3 Begins\n"
            "6:10   Execute"
        ))
        middle.addWidget(timeline, 3)

        event = FoundryCard("Event Details", "mechanics")
        event.addWidget(self._placeholder("Selected event details, assignment ownership, and handling notes will appear here."))
        event.addWidget(QPushButton("Add Custom Event"))
        middle.addWidget(event, 2)
        upper.addLayout(middle, 3)

        right = QVBoxLayout()
        right.setSpacing(8)

        mechanics = FoundryCard("Mechanics Reference", "open-book")
        mechanic_search = QLineEdit()
        mechanic_search.setPlaceholderText("Search mechanics…")
        mechanics.addWidget(mechanic_search)
        mechanic_list = QListWidget()
        mechanic_list.addItems(("Portal Spawn", "Heavy Attack", "Orbs", "Portal Adds", "Chains", "Execute"))
        mechanics.addWidget(mechanic_list)
        right.addWidget(mechanics, 2)

        detail = FoundryCard("Mechanic Details", "crossed-swords")
        detail.addWidget(self._placeholder(
            "Select a mechanic to show type, phase, priority, failure risk, handling notes, and responsible roles."
        ))
        right.addWidget(detail, 3)

        notes = FoundryCard("Quick Notes", "feather").make_parchment().set_watermark("feather", 0.12)
        notes.addWidget(self._placeholder("• Callout conventions\n• Phase reminders\n• Adjustment notes"))
        notes.set_header_action(QPushButton("Add Note"))
        right.addWidget(notes, 2)

        upper.addLayout(right, 3)
        root.addLayout(upper, 1)
        return tab

    def _connect_boss_selector(self) -> None:
        self.boss_combo.currentIndexChanged.connect(self._boss_changed)
        self.previous_boss_button.clicked.connect(lambda: self._step_boss(-1))
        self.next_boss_button.clicked.connect(lambda: self._step_boss(1))

    def _boss_rows_for_active_trial(self):
        rows = tuple(self.guide_service.encounter_summaries())
        current_trial = str(self.expedition.expedition.Expedition or "").strip().casefold()
        if not current_trial:
            return rows
        matching = tuple(
            row for row in rows
            if str(row.content_name or "").strip().casefold() == current_trial
        )
        return matching or rows

    def _load_boss_index(self) -> None:
        self._guide_summaries = self._boss_rows_for_active_trial()
        objective = str(self.expedition.expedition.Objective or "").strip().casefold()

        self.boss_combo.blockSignals(True)
        self.boss_combo.clear()
        for row in self._guide_summaries:
            self.boss_combo.addItem(row.name, row.encounter_id)
        self.boss_combo.blockSignals(False)

        if objective:
            match = next(
                (
                    index
                    for index, row in enumerate(self._guide_summaries)
                    if row.name.casefold() == objective
                ),
                -1,
            )
            if match >= 0:
                self.boss_combo.setCurrentIndex(match)

        if self.boss_combo.count() > 0 and self.boss_combo.currentIndex() < 0:
            self.boss_combo.setCurrentIndex(0)

        enabled = self.boss_combo.count() > 0
        self.previous_boss_button.setEnabled(enabled)
        self.next_boss_button.setEnabled(enabled)

    def _boss_changed(self, index: int) -> None:
        if index < 0 or index >= len(self._guide_summaries):
            return
        row = self._guide_summaries[index]
        self.expedition.expedition.Objective = row.name
        if hasattr(self, "status"):
            self.status.info(f"Selected boss: {row.name}.")

    def _step_boss(self, delta: int) -> None:
        count = self.boss_combo.count()
        if count <= 0:
            return
        self.boss_combo.setCurrentIndex((self.boss_combo.currentIndex() + delta) % count)

    def _mechanics_tab(self) -> QWidget:
        tab = QWidget()
        root = QVBoxLayout(tab)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        intro = FoundryCard("Mechanics Map", "crossed-swords").set_watermark("compass", 0.025)
        intro.addWidget(QLabel(
            "Build a clean tactical picture of the fight. Drag the boss, role markers, portals, AOEs, and stack points into place. "
            "Use 2 Bosses for paired encounters such as twins."
        ))
        root.addWidget(intro)

        board_card = FoundryCard("Interactive Positioning Board", "treasure-map")
        self.encounter_board = EncounterBoard()
        self.encounter_board.raid_plan_member_labels_resolver = self._raid_plan_member_labels
        self.encounter_board.snapshotSaved.connect(self._positioning_snapshot_saved)
        self._install_attach_to_control()
        self._install_raid_plan_map_controls()
        board_card.addWidget(self.encounter_board)
        root.addWidget(board_card, 1)

        self._load_positioning_preview(self.encounter_board.snapshot_path)
        return tab

    def _install_raid_plan_map_controls(self) -> None:
        board = getattr(self, "encounter_board", None)
        if board is None or board.layout() is None:
            return
        controls = QWidget()
        row = QHBoxLayout(controls)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        button = QPushButton("Save Map to Raid Plan")
        button.setObjectName("saveRaidMapToPlanButton")
        button.setToolTip(
            "Save the full editable Raid Map layout locally and link it to the selected Raid Plan."
        )
        button.clicked.connect(self._save_raid_map_to_plan)
        self.save_raid_map_to_plan_button = button
        row.addWidget(button)

        self.save_raid_map_to_finch_button = QPushButton("Save Map to Finch (WebP)")
        self.save_raid_map_to_finch_button.setObjectName("saveRaidMapToFinchWebpButton")
        self.save_raid_map_to_finch_button.setProperty("primary", True)
        self.save_raid_map_to_finch_button.setToolTip(
            "Capture this Raid Map, flatten it to a compact WebP, save it to Finch, and republish the Raid Plan so the mobile site can display it."
        )
        self.save_raid_map_to_finch_button.clicked.connect(self._save_raid_map_to_finch)
        row.addWidget(self.save_raid_map_to_finch_button)

        self.remove_raid_map_from_finch_button = QPushButton("Remove Map from Finch")
        self.remove_raid_map_from_finch_button.setToolTip(
            "Remove the selected encounter's published Raid Map preview from this Raid Plan and republish the plan. The local editable map is kept."
        )
        self.remove_raid_map_from_finch_button.clicked.connect(self._remove_raid_map_from_finch)
        row.addWidget(self.remove_raid_map_from_finch_button)

        board.layout().insertWidget(max(0, board.layout().count() - 1), controls)

    def _save_raid_map_to_plan(self):
        plan_id = str(self.raid_plan_combo.currentData() or "").strip()
        if not plan_id:
            self.status.warning("Select a saved Raid Plan before saving this map to it.")
            return None
        plan = self.raid_plan_repository.get(plan_id)
        if plan is None:
            self.status.warning("The selected Raid Plan no longer exists.")
            return None

        encounter_id = str(self.boss_combo.currentData() or "").strip()
        if not encounter_id:
            self.status.warning("Select a boss encounter before saving this map to the Raid Plan.")
            return None
        label = f"{plan.name} • {self.boss_combo.currentText() or 'Raid Map'}"
        self.encounter_board.raid_plan_id = plan_id

        # The editable Encounters source always owns stable seat labels such as
        # Tank1 / Healer2 / DD4. Player identities are a Raid Plan projection,
        # never persisted back into the reusable authoring layout.
        toggle_names = getattr(self.encounter_board, "_toggle_player_name_labels", None)
        if callable(toggle_names):
            toggle_names(self.encounter_board, False)
        self.encounter_board.save_state()
        self.raid_map_store.save_plan_layout(
            plan_id,
            self.encounter_board.state_path,
            encounter_id=encounter_id,
            label=label,
        )

        # Live Raid and Finch intentionally share the same player-labelled image.
        # Render names only for the flattened Raid Plan projection, then restore
        # the editor to stable chair labels immediately afterward.
        if callable(toggle_names):
            toggle_names(self.encounter_board, True)
        self.encounter_board.capture_snapshot()
        record = self.raid_map_store.import_map(
            encounter_id,
            self.encounter_board.snapshot_path,
            label=label,
        )
        if callable(toggle_names):
            toggle_names(self.encounter_board, False)

        self.raid_section_state.set_linked_raid_map_id(
            plan_id,
            encounter_id,
            record.map_id,
        )
        self.status.success(
            f"Saved Raid Plan map for {plan.name}: Encounters keeps seat labels; Live Raid/Finch use player names."
        )
        return record

    def _remove_raid_map_from_finch(self) -> None:
        plan_id = str(self.raid_plan_combo.currentData() or "").strip()
        encounter_id = str(self.boss_combo.currentData() or "").strip()
        encounter_name = str(self.boss_combo.currentText() or "").strip()
        if not plan_id or not encounter_id:
            self.status.warning("Select a saved Raid Plan and boss before removing its Finch map.")
            return

        removed = self.raid_section_state.remove_finch_raid_map_preview(plan_id, encounter_id)
        if not removed:
            self.status.info(f"No Finch Raid Map preview is attached to {encounter_name or encounter_id}.")
            return

        try:
            from services.finch_shared_publish_service import publish_raid_plan_to_finch
            publish_raid_plan_to_finch(
                database_path=Path(get_data_dir()) / "eso.db",
                raid_plans_path=Path(get_data_dir()) / "raid_plans.json",
                plan_id=plan_id,
                settings_path=Path("settings.json"),
            )
        except Exception as exc:
            self.status.error(
                f"Removed the local Finch map link, but Raid Plan republish failed: {exc}"
            )
            return
        self.status.success(
            f"Removed {encounter_name or encounter_id} Raid Map from Finch. Local map kept."
        )

    def _save_raid_map_to_finch(self) -> None:
        plan_id = str(self.raid_plan_combo.currentData() or "").strip()
        if not plan_id:
            self.status.warning("Select a saved Raid Plan before sending this map to Finch.")
            return
        plan = self.raid_plan_repository.get(plan_id)
        if plan is None:
            self.status.warning("The selected Raid Plan no longer exists.")
            return

        encounter_id = str(self.boss_combo.currentData() or "").strip()
        encounter_name = str(self.boss_combo.currentText() or "").strip()
        if not encounter_id:
            self.status.warning("Select a boss encounter before sending this map to Finch.")
            return

        if self._finch_raid_map_future is not None and not self._finch_raid_map_future.done():
            self.status.info("A Raid Map WebP publish is already running.")
            return

        # Save once. The resulting linked preview is the exact player-labelled
        # image consumed by both Live Raid and Finch.
        record = self._save_raid_map_to_plan()
        if record is None:
            return
        source = self.raid_map_store.resolve_path(record)
        label = f"{plan.name} • {encounter_name or 'Raid Map'}"

        self.save_raid_map_to_finch_button.setEnabled(False)
        self.status.info("Converting the Live Raid map to WebP and saving it to Finch…")
        self._finch_raid_map_future = _FINCH_RAID_MAP_EXECUTOR.submit(
            publish_raid_map_and_plan_to_finch,
            source=source,
            plan_id=plan_id,
            encounter_id=encounter_id,
            encounter_name=encounter_name,
            map_label=label,
            data_dir=get_data_dir(),
            settings_path=Path("settings.json"),
        )
        self._finch_raid_map_timer.start()

    def _poll_finch_raid_map_publish(self) -> None:
        future = self._finch_raid_map_future
        if future is None or not future.done():
            return
        self._finch_raid_map_timer.stop()
        self._finch_raid_map_future = None
        self.save_raid_map_to_finch_button.setEnabled(True)
        try:
            preview = future.result()
        except Exception as exc:
            self.status.error(f"Finch Raid Map WebP publish failed: {exc}")
            return
        self.status.success(
            f"Saved {preview.encounter_name} to Finch as WebP and republished the Raid Plan."
        )

    def _populate_raid_plan_context(self) -> None:
        if not hasattr(self, "raid_plan_combo"):
            return
        remembered = str(
            getattr(getattr(self, "encounter_board", None), "raid_plan_id", "") or ""
        ).strip()
        current = str(self.raid_plan_combo.currentData() or "").strip()
        wanted = current or remembered

        self.raid_plan_combo.blockSignals(True)
        self.raid_plan_combo.clear()
        self.raid_plan_combo.addItem("None", "")
        try:
            plans = self.raid_plan_repository.list_plans()
        except Exception as exc:
            plans = ()
            if hasattr(self, "status"):
                self.status.warning(f"Raid Plans could not be loaded: {exc}")
        for plan in plans:
            label = plan.name
            if plan.trial_id:
                label += f" • {plan.trial_id}"
            self.raid_plan_combo.addItem(label, plan.plan_id)
        index = self.raid_plan_combo.findData(wanted) if wanted else 0
        self.raid_plan_combo.setCurrentIndex(index if index >= 0 else 0)
        self.raid_plan_combo.blockSignals(False)

        if hasattr(self, "encounter_board"):
            self.encounter_board.raid_plan_id = str(
                self.raid_plan_combo.currentData() or ""
            ).strip()

    def _raid_plan_member_labels(self) -> dict[str, str]:
        plan_id = str(getattr(self.encounter_board, "raid_plan_id", "") or "").strip()
        if not plan_id:
            return {}
        plan = self.raid_plan_repository.get(plan_id)
        if plan is None:
            return {}
        return {
            member.seat_id: (member.gamertag or member.character_name or "")
            for member in plan.members
            if member.gamertag or member.character_name
        }

    def _load_saved_plan_layout_for_current_encounter(self, plan_id: str) -> bool:
        encounter_id = str(self.boss_combo.currentData() or "").strip()
        if not plan_id or not encounter_id:
            return False
        record = self.raid_map_store.latest_plan_layout(plan_id, encounter_id)
        if record is None:
            return False
        path = self.raid_map_store.resolve_path(record)
        self.encounter_board.raid_plan_id = plan_id
        if not self.encounter_board.load_state_from(path):
            return False
        self.encounter_board.view.fit_arena()
        self.encounter_board.capture_snapshot()
        self._load_positioning_preview(self.encounter_board.snapshot_path)
        return True

    def open_saved_plan_map(self, plan_id: str) -> bool:
        """Open the editable Raid Map saved for one exact Raid Plan."""
        plan_id = str(plan_id or "").strip()
        if not plan_id:
            return False
        plan = self.raid_plan_repository.get(plan_id)
        if plan is None:
            self.status.warning("That saved Raid Plan no longer exists.")
            return False

        self._populate_raid_plan_context()
        index = self.raid_plan_combo.findData(plan_id)
        if index >= 0:
            self.raid_plan_combo.setCurrentIndex(index)

        rows = tuple(self.guide_service.encounter_summaries())
        wanted_trial = str(plan.trial_id or "").strip().casefold()
        matching = tuple(
            row for row in rows
            if str(row.content_id or "").strip().casefold() == wanted_trial
            or str(row.content_name or "").strip().casefold() == wanted_trial
        )
        if matching:
            self._guide_summaries = matching
            self.boss_combo.blockSignals(True)
            self.boss_combo.clear()
            for row in matching:
                self.boss_combo.addItem(row.name, row.encounter_id)
            self.boss_combo.blockSignals(False)

        links = self.raid_section_state.raid_map_links(plan_id)
        preferred = next(
            (
                encounter_id
                for encounter_id in links
                if self.raid_map_store.latest_plan_layout(plan_id, encounter_id) is not None
            ),
            "",
        )
        if preferred:
            boss_index = self.boss_combo.findData(preferred)
            if boss_index >= 0:
                self.boss_combo.setCurrentIndex(boss_index)

        for tab_index in range(self.section_tabs.count()):
            if str(self.section_tabs.tabText(tab_index) or "").strip().casefold() == "mechanics":
                self.section_tabs.setCurrentIndex(tab_index)
                break

        if self._load_saved_plan_layout_for_current_encounter(plan_id):
            self.status.success(
                f"Loaded saved Raid Map for {plan.name} • {self.boss_combo.currentText()}."
            )
            return True

        self.encounter_board.raid_plan_id = plan_id
        self.status.warning(
            f"No editable Raid Map is saved for {plan.name} • {self.boss_combo.currentText()}."
        )
        return False

    def _raid_plan_context_changed(self, *_args) -> None:
        if not hasattr(self, "encounter_board"):
            return
        self.encounter_board.raid_plan_id = str(
            self.raid_plan_combo.currentData() or ""
        ).strip()
        refresh = getattr(self.encounter_board, "refresh_player_name_labels", None)
        if callable(refresh):
            refresh()
        self.encounter_board.save_state()

    @staticmethod
    def _layout_containing_widget(layout, target):
        if layout is None:
            return None
        for index in range(layout.count()):
            item = layout.itemAt(index)
            if item.widget() is target:
                return layout, index
            child = item.layout()
            if child is not None:
                found = EncountersPage._layout_containing_widget(child, target)
                if found is not None:
                    return found
            widget = item.widget()
            if widget is not None and widget.layout() is not None:
                found = EncountersPage._layout_containing_widget(widget.layout(), target)
                if found is not None:
                    return found
        return None

    def _install_attach_to_control(self) -> None:
        if not hasattr(self, "encounter_board"):
            return
        upload_button = next(
            (
                button
                for button in self.encounter_board.findChildren(QPushButton)
                if button.text().strip() == "Upload Map"
            ),
            None,
        )
        self.attach_raid_map_button = QPushButton("Attach to…")
        self.attach_raid_map_button.setToolTip(
            "Capture this Raid Map and attach it directly to a Mechanics & Timelines encounter."
        )
        self.attach_raid_map_button.clicked.connect(self._attach_current_map_to_encounter)

        if upload_button is not None:
            found = self._layout_containing_widget(self.encounter_board.layout(), upload_button)
            if found is not None:
                layout, index = found
                layout.insertWidget(index + 1, self.attach_raid_map_button)
                return

        root = self.encounter_board.layout()
        if root is not None:
            root.insertWidget(max(0, root.count() - 2), self.attach_raid_map_button)

    def _attach_current_map_to_encounter(self) -> None:
        summaries = tuple(self.guide_service.encounter_summaries())
        if not summaries:
            self.status.warning("No Mechanics & Timelines encounters are available.")
            return

        active_trial = str(self.expedition.expedition.Expedition or "").strip().casefold()
        matching = tuple(
            row
            for row in summaries
            if active_trial
            and str(row.content_name or "").strip().casefold() == active_trial
        )
        choices = matching or summaries

        selected_encounter_id = str(self.boss_combo.currentData() or "").strip()
        labels = [
            row.name if matching else f"{row.content_name} • {row.name}"
            for row in choices
        ]
        default_index = next(
            (
                index
                for index, row in enumerate(choices)
                if row.encounter_id == selected_encounter_id
            ),
            0,
        )
        selected, accepted = QInputDialog.getItem(
            self,
            "Attach Raid Map",
            "Mechanics & Timelines encounter:",
            labels,
            default_index,
            False,
        )
        if not accepted:
            return

        index = labels.index(selected)
        encounter = choices[index]

        try:
            self.encounter_board.capture_snapshot()
            record = self.raid_map_store.import_map(
                encounter.encounter_id,
                self.encounter_board.snapshot_path,
                label=f"{encounter.name} Positioning",
            )
            plan_id = str(self.raid_plan_combo.currentData() or "").strip()
            if plan_id:
                self.raid_section_state.set_linked_raid_map_id(
                    plan_id,
                    encounter.encounter_id,
                    record.map_id,
                )
        except Exception as exc:
            self.status.error(f"Raid Map attachment failed: {exc}")
            return

        if plan_id:
            plan = self.raid_plan_repository.get(plan_id)
            plan_name = plan.name if plan is not None else plan_id
            self.status.success(
                f"Attached Raid Map to {encounter.name} and linked it to Raid Plan {plan_name}."
            )
        else:
            self.status.success(
                f"Attached Raid Map to Mechanics & Timelines • {encounter.name}."
            )

    def _positioning_snapshot_saved(self, path: str):
        self._load_positioning_preview(Path(path))
        if hasattr(self, "status"):
            self.status.success("Positioning captured. Assignments preview updated.")

    def _load_positioning_preview(self, path: Path):
        if not hasattr(self, "positioning_preview"):
            return
        if not path.exists():
            return
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            return
        scaled = pixmap.scaled(
            760,
            360,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.positioning_preview.setPixmap(scaled)
        self.positioning_preview.setToolTip("Latest captured positioning from the Mechanics tactical board")

    def _empty_section(self, text: str) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        card = FoundryCard("Workspace", "notebook").set_watermark("compass", 0.035)
        card.addWidget(self._placeholder(text, centered=True))
        layout.addWidget(card, 1)
        return tab

    def refresh_context(self):
        current = self.expedition.expedition
        trial = current.Expedition or "No Active Expedition"
        difficulty = current.Difficulty or ""

        self.active_trial.setText(f"{trial}{f' ({difficulty})' if difficulty else ''}")
        self.group_size.setText("— / —")
        self._populate_raid_plan_context()
        self._load_boss_index()
