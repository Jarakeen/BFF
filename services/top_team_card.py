# widgets/top_team_card.py
#
# "Top Ranked Team" card for the Capabilities Desk: pick a trial,
# pick a boss, fetch the top-ranking log's roster from ESO Logs,
# and show each player's role, class, gear sets, and skills.
#
# Wide-table by default (FoundryTable's columns stretch to fill the
# card already); gear/skills cells also carry the full untruncated
# list as a hover tooltip for players with a lot of watched effects,
# so both of the layouts the user asked to compare are present at
# once -- widen the card, or hover a cell, whichever reads better in
# practice.

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)

from services.top_team_service import TopTeamService
from services.esologs_client import EsoLogsApiError
from models.top_team_model import TopTeamResult

from ui.components.foundry_button import ButtonRole, FoundryButton
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_status_bar import FoundryStatusBar
from ui.components.foundry_table import FoundryTable

_TABLE_COLUMNS = ["Role", "Class", "Player", "Gear Sets", "Skills", "Mundus"]

_GEAR_PREVIEW_COUNT = 3
_SKILL_PREVIEW_COUNT = 4


class TopTeamCard(FoundryCard):
    """
    Self-contained card: owns its own trial/boss pickers and result
    table. The page only needs to construct it with a way to get a
    freshly-configured TopTeamService (credentials can change on the
    Settings page, so this asks for a factory rather than a fixed
    service instance -- same pattern CapabilitiesPage already uses
    for CapabilityService).
    """

    fetchFailed = Signal(str)
    fetchSucceeded = Signal(str)

    def __init__(self, service_factory, parent=None):
        super().__init__(title="Top Ranked Team", icon="achievement", parent=parent)

        self._service_factory = service_factory
        self._trials: list[dict] = []

        self._build_ui()
        self._connect_signals()

        self.load_trials()

    # --------------------------------------------------
    # UI
    # --------------------------------------------------

    def _build_ui(self):

        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(6)

        picker_row = QHBoxLayout()
        picker_row.setSpacing(8)

        self.trial_combo = QComboBox()
        self.trial_combo.setMinimumWidth(220)
        self.trial_combo.setPlaceholderText("Choose a trial...")

        self.encounter_combo = QComboBox()
        self.encounter_combo.setMinimumWidth(200)
        self.encounter_combo.setPlaceholderText("Choose a boss...")
        self.encounter_combo.setEnabled(False)

        self.fetch_button = FoundryButton(
            "Fetch Top Team",
            role=ButtonRole.PRIMARY,
            compact=True,
        )
        self.fetch_button.setEnabled(False)

        self.reload_trials_button = FoundryButton(
            "Reload Trials",
            role=ButtonRole.SECONDARY,
            compact=True,
        )

        picker_row.addWidget(self.trial_combo)
        picker_row.addWidget(self.encounter_combo)
        picker_row.addWidget(self.fetch_button)
        picker_row.addWidget(self.reload_trials_button)
        picker_row.addStretch()

        root_layout.addLayout(picker_row)

        self.table = FoundryTable(columns=_TABLE_COLUMNS, rows=[])
        self.table.setMinimumHeight(220)

        root_layout.addWidget(self.table)

        self.status = FoundryStatusBar()

        root_layout.addWidget(self.status)

        self.addWidget(root)

    def _connect_signals(self):

        self.trial_combo.currentIndexChanged.connect(self._on_trial_changed)

        self.encounter_combo.currentIndexChanged.connect(self._on_encounter_changed)

        self.fetch_button.clicked.connect(self.fetch_top_team)

        self.reload_trials_button.clicked.connect(self.load_trials)

    # --------------------------------------------------
    # Trial / boss loading
    # --------------------------------------------------

    def load_trials(self):
        """
        Populate the trial dropdown. Requires valid ESO Logs
        credentials (same Settings-page Client ID/Secret the rest of
        the Capabilities page uses), so this can legitimately fail on
        first load if they aren't set yet -- that's reported through
        the status bar, not a popup, so it doesn't block opening the
        page.
        """

        self.status.info("Loading trial list from ESO Logs...")

        try:

            service = self._service_factory()

            self._trials = service.list_trials()

        except EsoLogsApiError as exc:

            self.status.error(str(exc))

            return

        except Exception as exc:

            self.status.error(f"Failed to load trials: {exc}")

            return

        self.trial_combo.blockSignals(True)

        self.trial_combo.clear()

        for trial in self._trials:
            self.trial_combo.addItem(trial["name"], trial)

        self.trial_combo.setCurrentIndex(-1)

        self.trial_combo.blockSignals(False)

        # Signals were blocked above, so the trial->encounter cascade
        # didn't fire -- clear the encounter picker and Fetch button
        # by hand so a reload doesn't leave a stale boss selected for
        # a trial that's no longer chosen.
        self.encounter_combo.blockSignals(True)
        self.encounter_combo.clear()
        self.encounter_combo.setEnabled(False)
        self.encounter_combo.blockSignals(False)

        self.fetch_button.setEnabled(False)

        if self._trials:
            self.status.info(f"{len(self._trials)} trial(s) loaded. Choose one above.")
        else:
            self.status.warning("ESO Logs returned no trial zones.")

    def _on_trial_changed(self, index: int):

        self.encounter_combo.blockSignals(True)

        self.encounter_combo.clear()

        self.fetch_button.setEnabled(False)

        if index < 0:

            self.encounter_combo.setEnabled(False)

            self.encounter_combo.blockSignals(False)

            return

        trial = self.trial_combo.itemData(index)

        for encounter in (trial or {}).get("encounters", []):
            self.encounter_combo.addItem(encounter["name"], encounter)

        self.encounter_combo.setCurrentIndex(-1)

        self.encounter_combo.setEnabled(True)

        self.encounter_combo.blockSignals(False)

    def _on_encounter_changed(self, index: int):

        self.fetch_button.setEnabled(index >= 0)

    # --------------------------------------------------
    # Fetch
    # --------------------------------------------------

    def fetch_top_team(self):

        trial_index = self.trial_combo.currentIndex()

        encounter_index = self.encounter_combo.currentIndex()

        if trial_index < 0 or encounter_index < 0:

            self.status.warning("Choose a trial and a boss first.")

            return

        trial = self.trial_combo.itemData(trial_index)

        encounter = self.encounter_combo.itemData(encounter_index)

        self.status.info(
            f"Fetching the top-ranked {encounter['name']} log from ESO Logs..."
        )

        self.fetch_button.setEnabled(False)

        try:

            service = self._service_factory()

            result = service.get_top_team(
                zone_id=trial["id"],
                zone_name=trial["name"],
                encounter_id=encounter["id"],
                encounter_name=encounter["name"],
            )

        except EsoLogsApiError as exc:

            self.status.error(str(exc))

            self.fetchFailed.emit(str(exc))

            return

        except Exception as exc:

            self.status.error(f"Fetch failed: {exc}")

            self.fetchFailed.emit(str(exc))

            return

        finally:

            self.fetch_button.setEnabled(True)

        self._render_result(result)

        self.status.success(
            f"{len(result.Players)} player build(s) loaded for "
            f"{result.TrialName} -- {result.EncounterName}."
        )

        self.fetchSucceeded.emit(result.ReportCode)

    # --------------------------------------------------
    # Rendering
    # --------------------------------------------------

    _ROLE_ORDER = {"tank": 0, "healer": 1, "dps": 2}

    def _render_result(self, result: TopTeamResult):

        players = sorted(
            result.Players,
            key=lambda p: (self._ROLE_ORDER.get(p.Role, 9), p.ClassName, p.Name),
        )

        rows = [self._player_row(p) for p in players]

        self.table.set_data(_TABLE_COLUMNS, rows)

        self._apply_tooltips(players)

    @staticmethod
    def _player_row(player) -> list:

        role_key = player.Role or "dps"

        role_label = role_key.capitalize()

        gear_preview = TopTeamCard._preview(player.GearSets, _GEAR_PREVIEW_COUNT)

        skills_preview = TopTeamCard._preview(player.Abilities, _SKILL_PREVIEW_COUNT)

        return [
            {"badge": role_label, "scale": "role", "key": role_key},
            player.ClassName or "--",
            player.Name or "--",
            gear_preview or "--",
            skills_preview or "--",
            player.Mundus or "--",
        ]

    @staticmethod
    def _preview(items: list[str], count: int) -> str:

        if not items:
            return ""

        shown = ", ".join(items[:count])

        if len(items) > count:
            shown += f", +{len(items) - count} more"

        return shown

    def _apply_tooltips(self, players: list):
        """
        Gear/Skills columns show a short preview; the full list is
        always available on hover so a truncated cell never actually
        hides information.
        """

        gear_col = _TABLE_COLUMNS.index("Gear Sets")

        skills_col = _TABLE_COLUMNS.index("Skills")

        for row, player in enumerate(players):

            gear_item = self.table.item(row, gear_col)

            if gear_item is not None and player.GearSets:
                gear_item.setToolTip("\n".join(player.GearSets))

            skills_item = self.table.item(row, skills_col)

            if skills_item is not None and player.Abilities:
                skills_item.setToolTip("\n".join(player.Abilities))
