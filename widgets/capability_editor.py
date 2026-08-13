# widgets/capability_editor.py
#
# One raid team member's Capabilities panel: which ESO Logs
# report/fight to read, which buffs/debuffs/skills to watch
# (with suggestions from equipped gear sets), and the
# resulting uptime table. Holds no network/DB access of its
# own -- the page owns the services and calls into this
# widget's public API, same convention as widgets/build_editor.py.

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QComboBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
)

from ui.components.foundry_card import FoundryCard
from ui.components.foundry_button import ButtonRole, FoundryButton
from ui.components.foundry_table import FoundryTable
from ui.components.foundry_empty_state import FoundryEmptyState

from models.capability_model import CapabilityProfile, WatchEntry, UptimeResult


class CapabilityEditor(QWidget):

    nameChanged = Signal(str)

    fetchRequested = Signal()
    suggestRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self._last_results: list[UptimeResult] = []
        self._last_fight_name: str = ""
        self._last_fight_duration: float = 0.0

        self.build_ui()

    # --------------------------------------------------
    # UI
    # --------------------------------------------------

    def build_ui(self):

        root = QVBoxLayout(self)

        root.setContentsMargins(0, 0, 0, 0)

        root.setSpacing(12)

        root.addWidget(self._build_source_card())
        root.addWidget(self._build_watch_card())
        root.addWidget(self._build_results_card())

        root.addStretch()

    def _build_source_card(self) -> FoundryCard:

        card = FoundryCard("Report Source")

        self.member_name = QLineEdit()
        self.member_name.setPlaceholderText("Raid member name (for this tab's label)")
        self.member_name.textChanged.connect(self.nameChanged.emit)

        self.report_code = QLineEdit()
        self.report_code.setPlaceholderText(
            "Report code, e.g. FPy6Tc9BzwQNbfVK "
            "(from esologs.com/reports/<code>)"
        )

        self.fight_id = QLineEdit()
        self.fight_id.setPlaceholderText("Fight #, e.g. 43")
        self.fight_id.setFixedWidth(80)

        self.boss_active_seconds = QLineEdit()
        self.boss_active_seconds.setPlaceholderText(
            "Optional -- seconds the boss was actually damageable"
        )

        self.equipped_sets = QLineEdit()
        self.equipped_sets.setPlaceholderText(
            "Equipped sets, comma-separated (used for suggestions)"
        )

        self.fetch_button = FoundryButton(
            "Fetch from ESO Logs",
            role=ButtonRole.PRIMARY,
        )

        self.fetch_button.clicked.connect(self.fetchRequested.emit)

        self.fight_summary_label = QLabel("No fight loaded yet.")

        self.fight_summary_label.setWordWrap(True)

        form = QFormLayout()

        form.addRow("Member", self.member_name)

        report_row = QHBoxLayout()

        report_row.addWidget(self.report_code, 3)
        report_row.addWidget(QLabel("Fight"))
        report_row.addWidget(self.fight_id, 1)

        form.addRow("Report", report_row)

        form.addRow("Boss Active Time", self.boss_active_seconds)
        form.addRow("Equipped Sets", self.equipped_sets)

        card.addLayout(form)

        actions = QHBoxLayout()

        actions.addWidget(self.fetch_button)
        actions.addStretch()

        card.addLayout(actions)

        card.addWidget(self.fight_summary_label)

        return card

    def _build_watch_card(self) -> FoundryCard:

        card = FoundryCard("Watch List")

        self.watch_list = QListWidget()

        self.watch_list.setMaximumHeight(160)

        self.new_watch_name = QComboBox()
        self.new_watch_name.setEditable(True)
        self.new_watch_name.setPlaceholderText("Buff, debuff, or skill name")

        self.new_watch_kind = QComboBox()
        self.new_watch_kind.addItems(["Buff", "Debuff", "Skill"])

        add_watch_button = FoundryButton(
            "+ Add",
            role=ButtonRole.SECONDARY,
            compact=True,
        )

        add_watch_button.clicked.connect(self._add_watch_from_inputs)

        remove_watch_button = FoundryButton(
            "Remove Selected",
            role=ButtonRole.DANGER,
            compact=True,
        )

        remove_watch_button.clicked.connect(self._remove_selected_watch)

        suggest_button = FoundryButton(
            "Suggest from Sets",
            role=ButtonRole.SECONDARY,
            compact=True,
        )

        suggest_button.clicked.connect(self.suggestRequested.emit)

        add_row = QHBoxLayout()

        add_row.addWidget(self.new_watch_name, 2)
        add_row.addWidget(self.new_watch_kind, 1)
        add_row.addWidget(add_watch_button)

        buttons_row = QHBoxLayout()

        buttons_row.addWidget(suggest_button)
        buttons_row.addWidget(remove_watch_button)
        buttons_row.addStretch()

        card.addWidget(self.watch_list)
        card.addLayout(add_row)
        card.addLayout(buttons_row)

        return card

    def _build_results_card(self) -> FoundryCard:

        card = FoundryCard("Uptime Results")

        self.results_table = FoundryTable(
            columns=[
                "Watching",
                "Type",
                "Uptime (Full Fight)",
                "Uptime (Boss Active)",
            ]
        )

        self.results_empty_state = FoundryEmptyState(
            "No results yet. Add a watch list, then Fetch from ESO Logs."
        )

        card.addWidget(self.results_empty_state)
        card.addWidget(self.results_table)

        self.results_table.setVisible(False)

        return card

    # --------------------------------------------------
    # Watch list
    # --------------------------------------------------

    def _add_watch_from_inputs(self):

        name = self.new_watch_name.currentText().strip()

        if not name:
            return

        self.add_watch(
            WatchEntry(Name=name, Kind=self.new_watch_kind.currentText())
        )

        self.new_watch_name.setCurrentText("")

    def add_watch(self, watch: WatchEntry):

        for existing in self.watches:

            if (
                existing.Name.casefold() == watch.Name.casefold()
                and existing.Kind == watch.Kind
            ):
                return

        item = QListWidgetItem(
            f"{watch.Name}  [{watch.Kind}]"
            + ("  (suggested)" if watch.Suggested else "")
        )

        item.setCheckState(Qt.CheckState.Checked)

        item.setData(Qt.ItemDataRole.UserRole, watch.to_dict())

        self.watch_list.addItem(item)

    def _remove_selected_watch(self):

        for item in self.watch_list.selectedItems():

            self.watch_list.takeItem(self.watch_list.row(item))

    def set_watch_name_choices(self, choices: list[str]):

        current = self.new_watch_name.currentText()

        self.new_watch_name.clear()

        self.new_watch_name.addItem("")

        self.new_watch_name.addItems(choices)

        self.new_watch_name.setCurrentText(current)

    @property
    def watches(self) -> list[WatchEntry]:

        watches = []

        for i in range(self.watch_list.count()):

            item = self.watch_list.item(i)

            data = item.data(Qt.ItemDataRole.UserRole) or {}

            watch = WatchEntry.from_dict(data)

            watches.append(watch)

        return watches

    @property
    def active_watches(self) -> list[WatchEntry]:
        """Only the checked entries -- what Fetch actually pulls."""

        active = []

        for i in range(self.watch_list.count()):

            item = self.watch_list.item(i)

            if item.checkState() != Qt.CheckState.Checked:
                continue

            data = item.data(Qt.ItemDataRole.UserRole) or {}

            active.append(WatchEntry.from_dict(data))

        return active

    # --------------------------------------------------
    # Results
    # --------------------------------------------------

    def show_fight_summary(self, summary: dict):

        kill_text = "Kill" if summary.get("kill") else "Wipe"

        boss_pct = summary.get("boss_percentage")

        boss_pct_text = (
            f", boss left at {boss_pct:.1f}%"
            if isinstance(boss_pct, (int, float)) and not summary.get("kill")
            else ""
        )

        self.fight_summary_label.setText(
            f"{summary.get('name', 'Fight')} -- {kill_text} -- "
            f"{summary.get('duration_seconds', 0):.1f}s{boss_pct_text}"
        )

    def show_results(self, results: list[UptimeResult]):

        if not results:

            self.results_table.setVisible(False)

            self.results_empty_state.setVisible(True)

            self.results_empty_state.set_message(
                "No matching buffs/debuffs/skills were found in this fight "
                "for the checked watch list."
            )

            return

        self.results_empty_state.setVisible(False)

        self.results_table.setVisible(True)

        rows = [
            [
                r.Name,
                r.Kind,
                f"{r.UptimePercentFull:.1f}%",
                f"{r.UptimePercentActive:.1f}%",
            ]
            for r in results
        ]

        self.results_table.set_data(
            ["Watching", "Type", "Uptime (Full Fight)", "Uptime (Boss Active)"],
            rows,
        )

    # --------------------------------------------------
    # Model
    # --------------------------------------------------

    @property
    def model(self) -> CapabilityProfile:

        return CapabilityProfile(
            Name=self.member_name.text().strip(),
            ReportCode=self.report_code.text().strip(),
            FightId=self.fight_id.text().strip(),
            EquippedSets=self.equipped_sets.text().strip(),
            BossActiveSeconds=self.boss_active_seconds.text().strip(),
            Watches=self.watches,
            LastResults=self._last_results,
            LastFightName=self._last_fight_name,
            LastFightDurationSeconds=self._last_fight_duration,
        )

    def load(self, model: CapabilityProfile):

        self.member_name.setText(model.Name)
        self.report_code.setText(model.ReportCode)
        self.fight_id.setText(model.FightId)
        self.equipped_sets.setText(model.EquippedSets)
        self.boss_active_seconds.setText(model.BossActiveSeconds)

        self.watch_list.clear()

        for watch in model.Watches:
            self.add_watch(watch)

        self._last_results = model.LastResults
        self._last_fight_name = model.LastFightName
        self._last_fight_duration = model.LastFightDurationSeconds

        if model.LastResults:

            self.show_results(model.LastResults)

            if model.LastFightName:

                self.show_fight_summary(
                    {
                        "name": model.LastFightName,
                        "kill": True,
                        "duration_seconds": model.LastFightDurationSeconds,
                    }
                )
        else:

            self.results_table.setVisible(False)

            self.results_empty_state.setVisible(True)

    def clear(self):

        self._last_results = []
        self._last_fight_name = ""
        self._last_fight_duration = 0.0

        self.load(CapabilityProfile())

    def record_results(self, summary: dict, results: list[UptimeResult]):

        self._last_results = results
        self._last_fight_name = summary.get("name", "")
        self._last_fight_duration = summary.get("duration_seconds", 0.0)

        self.show_fight_summary(summary)
        self.show_results(results)
