from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from minmax.base_character_state import BaseCharacterCalculator
from minmax.character_progression import AttributeAllocation
from models.build_model import BuildRoster, PlayerBuild
from services.build_service import BuildService
from services.expedition_service import ExpeditionService
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar
from ui.components.overview_key_stats_card import OverviewKeyStatsCard
from ui.foundry_page import FoundryPage
from ui.optimization_page import CORE_COVERAGE, EFFECT_ALIASES, CoverageItem


class CoverageSummaryCard(FoundryCard):
    """Overview-sized reuse of the Optimization coverage language."""

    def __init__(self, roster: BuildRoster, parent=None):
        super().__init__("Coverage Summary", "✓")
        self.set_badge("GROUP")
        self._render(roster)

    @staticmethod
    def _text_for_build(build: PlayerBuild) -> str:
        values = list(build.FrontBarSkills) + list(build.BackBarSkills)
        values += [
            build.FrontBarWeapon.Set,
            build.BackBarWeapon.Set,
            *[entry.get("Set", "") for entry in build.Armor.values()],
        ]
        return " ".join(str(value or "") for value in values).lower()

    def _resolve(self, roster: BuildRoster):
        coverage = {name: False for name in CORE_COVERAGE}
        providers: dict[str, int] = {name: 0 for name in CORE_COVERAGE}
        for member in roster.Members:
            haystack = self._text_for_build(member)
            for capability in CORE_COVERAGE:
                aliases = EFFECT_ALIASES.get(capability, (capability.lower(),))
                if any(alias in haystack for alias in aliases):
                    coverage[capability] = True
                    providers[capability] += 1
        return coverage, providers

    def _render(self, roster: BuildRoster):
        coverage, providers = self._resolve(roster)
        grid = QVBoxLayout()
        total = len(CORE_COVERAGE)
        columns = 3
        rows = (total + columns - 1) // columns
        for column in range(columns):
            column_widget = QWidget()
            column_layout = QVBoxLayout(column_widget)
            column_layout.setContentsMargins(0, 0, 0, 0)
            column_layout.setSpacing(2)
            for row in range(column * rows, min((column + 1) * rows, total)):
                name = CORE_COVERAGE[row]
                column_layout.addWidget(CoverageItem(name, coverage[name], providers[name]))
            grid.addWidget(column_widget)
        self.addLayout(grid)
        covered = sum(coverage.values())
        self.addWidget(QLabel(f"{covered}/{total} watch-list capabilities represented in saved builds."))


class PlayerCard(FoundryCard):
    def __init__(self, parent=None):
        super().__init__("Player", "♜")
        self.name_label = QLabel("No build selected")
        self.name_label.setProperty("overviewPlayerName", True)
        self.detail_label = QLabel("—")
        self.detail_label.setProperty("overviewPlayerDetail", True)
        self.addWidget(self.name_label)
        self.addWidget(self.detail_label)

    def update_build(self, build: PlayerBuild | None):
        if build is None:
            self.name_label.setText("No build selected")
            self.detail_label.setText("Create a character/build on Builds.")
            return
        name = build.Name or build.Gamertag or "Unnamed Player"
        details = " • ".join(value for value in (build.EsoClass, build.Race, build.Role) if value)
        self.name_label.setText(name)
        self.detail_label.setText(details or "Character details not yet entered")


class GearCard(FoundryCard):
    def __init__(self, parent=None):
        super().__init__("Current Gear", "♢")
        self.body = QLabel()
        self.body.setWordWrap(True)
        self.body.setProperty("overviewGear", True)
        self.addWidget(self.body)

    def update_build(self, build: PlayerBuild | None):
        if build is None:
            self.body.setText("No build selected.")
            return
        entries: list[str] = []
        for slot in ("Head", "Shoulders", "Chest", "Hands", "Waist", "Legs", "Feet"):
            entry = build.Armor.get(slot, {})
            set_name = entry.get("Set", "")
            if set_name:
                entries.append(f"{slot}: {set_name}")
        for label, slot in (
            ("Front", build.FrontBarWeapon),
            ("Back", build.BackBarWeapon),
            ("Necklace", build.Necklace),
            ("Ring 1", build.Ring1),
            ("Ring 2", build.Ring2),
        ):
            if slot.Set:
                entries.append(f"{label}: {slot.Set}")
        self.body.setText("\n".join(entries[:10]) if entries else "No gear entered for this build.")


class OperationsConsole(FoundryPage):
    """Raid Engine Overview, modeled after the supplied console reference."""

    def __init__(self, expedition: ExpeditionService, parent=None):
        super().__init__(parent)
        self.expedition = expedition
        self.build_service = BuildService(Path(__file__).resolve().parents[1] / "data" / "builds.json")
        self.roster = BuildRoster()
        self.calculator = BaseCharacterCalculator()
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        expedition = self.expedition.expedition
        encounter = expedition.Expedition or "No Active Expedition"
        difficulty = expedition.Difficulty or ""
        boss = expedition.Objective or "No Encounter Selected"

        self.header = FoundryHeader(
            title=boss,
            subtitle=f"{encounter}{f' ({difficulty})' if difficulty else ''}",
            department="Raid Engine • Overview",
        )
        self.set_header(self.header)

        self.player_combo = QComboBox()
        self.player_combo.currentIndexChanged.connect(self.refresh_selected)
        self.header.add_context_widget(self._context_field("PLAYER", self.player_combo))

        self.workspace = QWidget()
        self.layout = QVBoxLayout(self.workspace)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(10)
        self.add_workspace(self.workspace)

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

    @staticmethod
    def _clear_layout(layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
            elif item.layout() is not None:
                OperationsConsole._clear_layout(item.layout())

    def refresh(self):
        try:
            self.roster = self.build_service.load()
        except Exception as exc:
            self.roster = BuildRoster()
            self.status.error(f"Failed to load builds: {exc}")
            return

        self.player_combo.blockSignals(True)
        current = self.player_combo.currentData()
        self.player_combo.clear()
        for index, member in enumerate(self.roster.Members):
            label = member.Name or member.Gamertag or f"Player {index + 1}"
            if member.BuildName:
                label += f" • {member.BuildName}"
            self.player_combo.addItem(label, index)
        if current is not None:
            restored = self.player_combo.findData(current)
            if restored >= 0:
                self.player_combo.setCurrentIndex(restored)
        self.player_combo.blockSignals(False)
        self._render()

    def refresh_selected(self, _index=0):
        self._render()

    def _selected_build(self) -> PlayerBuild | None:
        index = self.player_combo.currentData()
        if index is None or not self.roster.Members:
            return None
        try:
            return self.roster.Members[int(index)]
        except (IndexError, TypeError, ValueError):
            return None

    def _render(self):
        self._clear_layout(self.layout)
        build = self._selected_build()

        self.layout.addWidget(CoverageSummaryCard(self.roster))

        player_row = QHBoxLayout()
        player_row.setSpacing(10)
        player_card = PlayerCard()
        player_card.update_build(build)
        gear_card = GearCard()
        gear_card.update_build(build)
        player_row.addWidget(player_card, 1)
        player_row.addWidget(gear_card, 1)
        self.layout.addLayout(player_row)

        if build is None:
            attributes = AttributeAllocation()
        else:
            attributes = AttributeAllocation(
                health=int(getattr(build, "AttributeHealth", 0)),
                magicka=int(getattr(build, "AttributeMagicka", 0)),
                stamina=int(getattr(build, "AttributeStamina", 0)),
            )
        state = self.calculator.calculate(attributes=attributes)
        stats = OverviewKeyStatsCard()
        stats.set_base(state)
        self.layout.addWidget(stats)

        note = FoundryCard("Calculation Notes", "i")
        note.addWidget(QLabel(
            "These values are calculator output, not imported ESO values. "
            "Use this panel to compare Foundry's math against ESO and other references."
        ))
        self.layout.addWidget(note)
        self.layout.addStretch(1)
        self.status.info(f"Overview ready • {len(self.roster.Members)} saved build(s) • calculator output shown above.")
