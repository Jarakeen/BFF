# widgets/top_team_card.py
#
# "Top Ranked Team" card for the Capabilities Desk: pick a trial,
# pick a boss, fetch the top-ranking log's roster from ESO Logs, and
# browse it as a vertical, role-sorted gear board (Tank / Healer /
# DD) rather than a flat list -- meant to be skimmed for "what's
# trending right now," not cross-referenced like a report.
#
# Built against models.top_team_model.TopTeamPlayer as it actually
# exists on this branch (Name / Role / GearSets only -- no class,
# skills, or Mundus fields), and services.top_team_service.TopTeamService
# as it actually exists (list_trials() / get_top_team(zone_id=,
# zone_name=, encounter_id=, encounter_name=)). Neither of those
# files is touched by this widget.
#
# Each section also surfaces which sets repeat across 2+ players in
# that role for this pull ("Trending in this pull") -- a cheap,
# honest signal computed from the one fetched log, not a claim about
# the wider meta.

from __future__ import annotations

from collections import Counter

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from models.top_team_model import TopTeamPlayer, TopTeamResult
from services.esologs_client import EsoLogsApiError

from ui.components.foundry_button import ButtonRole, FoundryButton
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_status_badge import FoundryStatusBadge
from ui.components.foundry_status_bar import FoundryStatusBar
from ui.theme.colors import Colors
from ui.theme.fonts import Fonts

_ROLE_SECTIONS = (
    ("tank", "Tank"),
    ("healer", "Healer"),
    ("dps", "DD"),
)

_TRENDING_MIN_COUNT = 2
_TRENDING_MAX_BADGES = 5

# Best-effort, community-knowledge list of gear sets a "support" DPS
# commonly runs (buffing/debuffing the group rather than pure
# personal damage). This isn't a field ESO Logs exposes -- it's a
# heuristic tag shown next to a DD player's name when 2+ of their
# sets match. The meta shifts, so treat it as a hint, not ground
# truth, and edit this list freely as sets rotate in and out.
KNOWN_SUPPORT_SET_NAMES = frozenset(
    name.casefold()
    for name in (
        "Powerful Assault",
        "Roaring Opportunist",
        "Pillar of Nirn",
        "Symphony of Blades",
        "Xoryn's Masterpiece",
        "Spaulder of Ruin",
        "Slivers of the Null Arca",
        "Trainee",
        "Zen's Redress",
    )
)


class TopTeamCard(FoundryCard):
    """
    Self-contained card: owns its own trial/boss pickers and its own
    role-sectioned gear display. The page only needs to construct it
    with a way to get a freshly-configured TopTeamService -- the
    constructor signature and public surface here are unchanged from
    what ui/capabilities_page.py already wires up.
    """

    fetchFailed = Signal(str)
    fetchSucceeded = Signal(str)

    def __init__(self, service_factory, parent=None):
        super().__init__(title="Top Ranked Team Gear", icon="achievement", parent=parent)

        self._service_factory = service_factory
        self._trials: list[dict] = []

        # role_key -> {"count_label", "trending_row", "trending_layout",
        #              "players_layout"}
        self._sections: dict[str, dict] = {}

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
        root_layout.setSpacing(10)

        #
        # Filters -- same trial / boss / fetch / reload row as
        # before.
        #

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

        root_layout.addLayout(picker_row)

        self.summary = QLabel(
            "Choose a trial and boss to inspect the top-ranked team's sets."
        )
        self.summary.setWordWrap(True)
        self.summary.setProperty("muted", True)
        self.summary.setStyleSheet(f"color: {Colors.TEXT_MUTED};")

        root_layout.addWidget(self.summary)

        #
        # Vertical, role-sectioned gear board.
        #

        self.board = QWidget()
        board_layout = QVBoxLayout(self.board)
        board_layout.setContentsMargins(0, 0, 0, 0)
        board_layout.setSpacing(4)

        for index, (role_key, role_label) in enumerate(_ROLE_SECTIONS):

            section_widget, section_refs = self._build_role_section(
                role_key, role_label
            )

            self._sections[role_key] = section_refs

            board_layout.addWidget(section_widget)

            if index < len(_ROLE_SECTIONS) - 1:

                divider = QFrame()
                divider.setFrameShape(QFrame.Shape.HLine)
                divider.setStyleSheet(f"color: {Colors.BORDER};")

                board_layout.addWidget(divider)

        root_layout.addWidget(self.board)

        self.status = FoundryStatusBar()

        root_layout.addWidget(self.status)

        self.addWidget(root)

    def _build_role_section(self, role_key: str, role_label: str):
        """
        Build one role section (header + optional trending-sets row
        + player list) and return (widget, refs) where refs holds
        the sub-widgets that need updating on every fetch.
        """

        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(6)

        #
        # Header: role badge + count.
        #

        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        role_badge = FoundryStatusBadge(role_label, scale="role", key=role_key)

        count_label = QLabel("0 players")
        count_label.setFont(Fonts.small())
        count_label.setStyleSheet(f"color: {Colors.TEXT_MUTED};")

        header_row.addWidget(role_badge)
        header_row.addWidget(count_label)
        header_row.addStretch()

        layout.addLayout(header_row)

        #
        # Trending-in-this-pull row: shown only when 2+ players in
        # this role share a set.
        #

        trending_row = QWidget()
        trending_layout = QHBoxLayout(trending_row)
        trending_layout.setContentsMargins(0, 0, 0, 0)
        trending_layout.setSpacing(6)

        trending_tag = QLabel("Trending:")
        trending_tag.setFont(Fonts.small())
        trending_tag.setStyleSheet(f"color: {Colors.GOLD};")

        trending_layout.addWidget(trending_tag)
        trending_layout.addStretch()

        trending_row.setVisible(False)

        layout.addWidget(trending_row)

        #
        # Player list.
        #

        players_container = QWidget()
        players_layout = QVBoxLayout(players_container)
        players_layout.setContentsMargins(12, 0, 0, 0)
        players_layout.setSpacing(8)

        empty_label = QLabel("Fetch a trial + boss to see this role's gear.")
        empty_label.setFont(Fonts.body())
        empty_label.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
        empty_label.setWordWrap(True)

        players_layout.addWidget(empty_label)

        layout.addWidget(players_container)

        refs = {
            "count_label": count_label,
            "trending_row": trending_row,
            "trending_layout": trending_layout,
            "players_layout": players_layout,
        }

        return section, refs

    def _connect_signals(self):

        self.trial_combo.currentIndexChanged.connect(self._on_trial_changed)

        self.encounter_combo.currentIndexChanged.connect(self._on_encounter_changed)

        self.fetch_button.clicked.connect(self.fetch_top_team)

        self.reload_button.clicked.connect(self.load_trials)

    # --------------------------------------------------
    # Trial / boss loading
    # --------------------------------------------------

    def load_trials(self):
        """
        Populate the trial dropdown. Requires valid ESO Logs
        credentials, so this can legitimately fail on first load if
        they aren't set yet -- reported through the status bar, not
        a popup, so it doesn't block opening the page.
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

    # --------------------------------------------------
    # Fetch
    # --------------------------------------------------

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

        self.status.success(f"Loaded {len(result.Players)} player gear list(s).")

        self.fetchSucceeded.emit(result.ReportCode)

    # --------------------------------------------------
    # Rendering
    # --------------------------------------------------

    def _render_result(self, result: TopTeamResult):

        self.summary.setText(
            f"{result.TrialName} \u00b7 {result.EncounterName} \u00b7 "
            f"top ranked report {result.ReportCode} / fight {result.FightId}"
        )

        by_role: dict[str, list[TopTeamPlayer]] = {
            role_key: [] for role_key, _ in _ROLE_SECTIONS
        }

        for player in result.Players:
            by_role.setdefault(player.Role, []).append(player)

        for role_key, _ in _ROLE_SECTIONS:

            self._render_section(role_key, by_role.get(role_key, []))

    def _render_section(self, role_key: str, players: list[TopTeamPlayer]):

        refs = self._sections[role_key]

        refs["count_label"].setText(
            f"{len(players)} player{'s' if len(players) != 1 else ''}"
        )

        self._clear_layout(refs["players_layout"])

        self._render_trending(role_key, players)

        if not players:

            empty_label = QLabel(
                "No players resolved for this role in this pull."
            )
            empty_label.setFont(Fonts.body())
            empty_label.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
            empty_label.setWordWrap(True)

            refs["players_layout"].addWidget(empty_label)

            return

        for player in sorted(players, key=lambda p: (p.Name or "").casefold()):

            refs["players_layout"].addWidget(
                self._build_player_row(role_key, player)
            )

    def _render_trending(self, role_key: str, players: list[TopTeamPlayer]):

        refs = self._sections[role_key]

        # keep_first=1 keeps only the "Trending:" tag label at index
        # 0 -- this also removes the trailing stretch along with the
        # old badges, so it must be re-added after the new badges
        # (addWidget appends in order; nothing is left to insert
        # "before" any more).
        self._clear_layout(refs["trending_layout"], keep_first=1)

        set_counts = Counter()

        for player in players:
            set_counts.update(set(player.GearSets))

        trending = [
            (name, count)
            for name, count in set_counts.most_common()
            if count >= _TRENDING_MIN_COUNT
        ][:_TRENDING_MAX_BADGES]

        if not trending:

            refs["trending_layout"].addStretch()

            refs["trending_row"].setVisible(False)

            return

        for name, count in trending:

            badge = FoundryStatusBadge(f"{name} x{count}", color=Colors.GOLD)

            refs["trending_layout"].addWidget(badge)

        refs["trending_layout"].addStretch()

        refs["trending_row"].setVisible(True)

    def _build_player_row(self, role_key: str, player: TopTeamPlayer) -> QWidget:

        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(10)

        # Small role-colored accent stripe so a role's players are
        # still visually identifiable if this card is ever skimmed
        # without reading the section headers.
        stripe = QFrame()
        stripe.setFixedWidth(3)
        stripe.setStyleSheet(
            f"background-color: {Colors.ROLE.get(role_key, Colors.BORDER)};"
        )

        row_layout.addWidget(stripe)

        text_column = QVBoxLayout()
        text_column.setSpacing(2)

        name_row = QHBoxLayout()
        name_row.setSpacing(6)

        name_label = QLabel(player.Name or "Unknown")
        name_label.setFont(Fonts.label())
        name_label.setStyleSheet(f"color: {Colors.TEXT};")

        name_row.addWidget(name_label)

        if role_key == "dps" and self._looks_like_support(player):

            support_badge = FoundryStatusBadge(
                "Support?", color=Colors.ACCENT_LIGHT
            )
            support_badge.setToolTip(
                "Heuristic guess based on 2+ known support-oriented "
                "sets -- not an ESO Logs field. Judge for yourself."
            )

            name_row.addWidget(support_badge)

        name_row.addStretch()

        text_column.addLayout(name_row)

        gear_text = ", ".join(player.GearSets) if player.GearSets else "No gear data."

        gear_label = QLabel(gear_text)
        gear_label.setFont(Fonts.body())
        gear_label.setStyleSheet(f"color: {Colors.GOLD_LIGHT};")
        gear_label.setWordWrap(True)
        gear_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        text_column.addWidget(gear_label)

        row_layout.addLayout(text_column, 1)

        return row

    @staticmethod
    def _looks_like_support(player: TopTeamPlayer) -> bool:

        matches = sum(
            1
            for gear_set in player.GearSets
            if gear_set.casefold() in KNOWN_SUPPORT_SET_NAMES
        )

        return matches >= 2

    @staticmethod
    def _clear_layout(layout, keep_first: int = 0):

        while layout.count() > keep_first:

            item = layout.takeAt(keep_first)

            widget = item.widget()

            if widget is not None:
                widget.deleteLater()

            nested = item.layout()

            if nested is not None:
                TopTeamCard._clear_layout(nested)
