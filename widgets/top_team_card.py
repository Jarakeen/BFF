from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from models.top_team_model import TopTeamResult
from services.esologs_client import EsoLogsApiError
from ui.components.foundry_button import ButtonRole, FoundryButton
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_status_bar import FoundryStatusBar


_ROLE_ORDER = {"tank": 0, "healer": 1, "dps": 2}
_ROLE_LABEL = {"tank": "Tank", "healer": "Healer", "dps": "DD"}


class TopTeamCard(FoundryCard):
    """Compact ESO Logs leaderboard roster focused only on equipped gear sets."""

    fetchFailed = Signal(str)
    fetchSucceeded = Signal(str)

    def __init__(self, service_factory, parent=None):
        super().__init__(title="Top Ranked Team Gear", icon="achievement", parent=parent)
        self._service_factory = service_factory
        self._trials: list[dict] = []
        self._build_ui()
        self._connect_signals()
        self.load_trials()

    def _build_ui(self):
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(7)

        picker_row = QHBoxLayout()
        picker_row.setSpacing(8)

        self.trial_combo = QComboBox()
        self.trial_combo.setMinimumWidth(210)
        self.trial_combo.setPlaceholderText("Choose a trial...")

        self.encounter_combo = QComboBox()
        self.encounter_combo.setMinimumWidth(190)
        self.encounter_combo.setPlaceholderText("Choose a boss...")
        self.encounter_combo.setEnabled(False)

        self.fetch_button = FoundryButton(
            "Fetch Team Gear",
            role=ButtonRole.PRIMARY,
            compact=True,
        )
        self.fetch_button.setEnabled(False)

        self.reload_button = FoundryButton(
            "Reload Trials",
            role=ButtonRole.SECONDARY,
            compact=True,
        )

        picker_row.addWidget(self.trial_combo)
        picker_row.addWidget(self.encounter_combo)
        picker_row.addWidget(self.fetch_button)
        picker_row.addWidget(self.reload_button)
        picker_row.addStretch()
        layout.addLayout(picker_row)

        self.summary = QLabel("Choose a trial and boss to inspect the top-ranked team's sets.")
        self.summary.setWordWrap(True)
        self.summary.setProperty("muted", True)
        layout.addWidget(self.summary)

        self.roster = QWidget()
        self.roster_layout = QVBoxLayout(self.roster)
        self.roster_layout.setContentsMargins(0, 0, 0, 0)
        self.roster_layout.setSpacing(3)
        layout.addWidget(self.roster)

        self.status = FoundryStatusBar()
        layout.addWidget(self.status)
        self.addWidget(root)

    def _connect_signals(self):
        self.trial_combo.currentIndexChanged.connect(self._on_trial_changed)
        self.encounter_combo.currentIndexChanged.connect(self._on_encounter_changed)
        self.fetch_button.clicked.connect(self.fetch_top_team)
        self.reload_button.clicked.connect(self.load_trials)

    def load_trials(self):
        self.status.info("Loading trial list from ESO Logs...")
        try:
            self._trials = self._service_factory().list_trials()
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

        self.encounter_combo.blockSignals(True)
        self.encounter_combo.clear()
        self.encounter_combo.setCurrentIndex(-1)
        self.encounter_combo.setEnabled(False)
        self.encounter_combo.blockSignals(False)
        self.fetch_button.setEnabled(False)

        if self._trials:
            self.status.info(f"{len(self._trials)} ranked zone(s) loaded. Choose a trial.")
        else:
            self.status.warning("ESO Logs returned no ranked trial zones.")

    def _on_trial_changed(self, index: int):
        self.encounter_combo.blockSignals(True)
        self.encounter_combo.clear()
        self.fetch_button.setEnabled(False)

        if index < 0:
            self.encounter_combo.setEnabled(False)
            self.encounter_combo.blockSignals(False)
            return

        trial = self.trial_combo.itemData(index) or {}
        for encounter in trial.get("encounters", []):
            self.encounter_combo.addItem(encounter["name"], encounter)
        self.encounter_combo.setCurrentIndex(-1)
        self.encounter_combo.setEnabled(True)
        self.encounter_combo.blockSignals(False)

    def _on_encounter_changed(self, index: int):
        self.fetch_button.setEnabled(index >= 0)

    def fetch_top_team(self):
        trial_index = self.trial_combo.currentIndex()
        encounter_index = self.encounter_combo.currentIndex()
        if trial_index < 0 or encounter_index < 0:
            self.status.warning("Choose a trial and boss first.")
            return

        trial = self.trial_combo.itemData(trial_index)
        encounter = self.encounter_combo.itemData(encounter_index)
        self.status.info(f"Fetching top-ranked {encounter['name']} team gear...")
        self.fetch_button.setEnabled(False)

        try:
            result = self._service_factory().get_top_team(
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
        self.status.success(f"Loaded {len(result.Players)} player gear list(s).")
        self.fetchSucceeded.emit(result.ReportCode)

    def _render_result(self, result: TopTeamResult):
        self._clear_roster()
        self.summary.setText(
            f"{result.TrialName} · {result.EncounterName} · "
            f"top ranked report {result.ReportCode} / fight {result.FightId}"
        )

        players = sorted(
            result.Players,
            key=lambda player: (
                _ROLE_ORDER.get(player.Role, 9),
                (player.Name or "").casefold(),
            ),
        )

        for player in players:
            self.roster_layout.addWidget(self._player_row(player))

        if not players:
            empty = QLabel("No player combatant information was returned for this ranked fight.")
            empty.setProperty("muted", True)
            self.roster_layout.addWidget(empty)

    def _player_row(self, player) -> QWidget:
        row = QFrame()
        row.setProperty("topTeamGearRow", True)
        row.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(6, 4, 6, 4)
        row_layout.setSpacing(8)

        role = QLabel(_ROLE_LABEL.get(player.Role, (player.Role or "DD").title()))
        role.setProperty("badge", True)
        role.setProperty("scale", "role")
        role.setProperty("key", player.Role or "dps")
        role.setAlignment(Qt.AlignmentFlag.AlignCenter)
        role.setFixedWidth(54)

        name = QLabel(player.Name or "Unknown")
        name.setMinimumWidth(150)
        name.setMaximumWidth(220)

        sets = QLabel(" · ".join(player.GearSets) if player.GearSets else "Set names unavailable")
        sets.setWordWrap(True)
        sets.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        sets.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        row_layout.addWidget(role)
        row_layout.addWidget(name)
        row_layout.addWidget(sets, 1)
        return row

    def _clear_roster(self):
        while self.roster_layout.count():
            item = self.roster_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
