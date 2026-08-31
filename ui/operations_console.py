from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from engine.config import DEFAULT_DATABASE, get_data_dir
from minmax.base_character_state import BaseCharacterCalculator
from minmax.character_progression import AttributeAllocation, CharacterProgression
from minmax.context_factory import BuildCalculationContextFactory
from minmax.gear_set_repository import GearSetRepository
from minmax.race_repository import RaceRepository
from models.build_model import BuildRoster, PlayerBuild
from services.build_service import BuildService
from services.expedition_service import ExpeditionService
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar
from ui.foundry_page import FoundryPage
from ui.optimization_page import CORE_COVERAGE, EFFECT_ALIASES


class OperationsConsole(FoundryPage):
    """Raid Engine command center: answer 'are we ready to pull?' at a glance."""

    def __init__(self, expedition: ExpeditionService, parent=None):
        super().__init__(parent)
        self.expedition = expedition
        self.build_service = BuildService(get_data_dir() / "builds.json")
        self.roster = BuildRoster()
        self.calculator = BaseCharacterCalculator()
        self.context_factory = BuildCalculationContextFactory(
            calculator=self.calculator,
            race_repository=RaceRepository(DEFAULT_DATABASE),
            gear_set_repository=GearSetRepository(DEFAULT_DATABASE),
        )
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        expedition = self.expedition.expedition
        trial = expedition.Expedition or "No Active Expedition"
        difficulty = expedition.Difficulty or ""
        boss = expedition.Objective or "No Encounter Selected"

        self.header = FoundryHeader(
            title="Raid Engine Overview",
            subtitle="At a glance. Are we ready?",
            department="Raid Engine • Overview",
        )
        self.set_header(self.header)

        encounter_box = QWidget()
        encounter_layout = QVBoxLayout(encounter_box)
        encounter_layout.setContentsMargins(0, 0, 0, 0)
        encounter_layout.setSpacing(1)
        small = QLabel("CURRENT ENCOUNTER")
        small.setProperty("sidebarHeading", True)
        encounter_layout.addWidget(small)
        encounter_layout.addWidget(QLabel(f"{trial}{f' ({difficulty})' if difficulty else ''}"))
        boss_label = QLabel(boss)
        boss_label.setProperty("overviewEncounterName", True)
        encounter_layout.addWidget(boss_label)
        self.header.add_context_widget(encounter_box)

        pull_box = QWidget()
        pull_layout = QVBoxLayout(pull_box)
        pull_layout.setContentsMargins(0, 0, 0, 0)
        pull_layout.setSpacing(1)
        pull_label = QLabel("PULL #—")
        pull_label.setProperty("overviewPullNumber", True)
        pull_layout.addWidget(pull_label)
        pull_layout.addWidget(QLabel("LAST WIPE   —"))
        self.header.add_context_widget(pull_box)

        ready = QLabel("✓  PULL READY")
        ready.setProperty("overviewReady", True)
        self.header.add_context_widget(ready)

        self.player_combo = QComboBox()
        self.player_combo.currentIndexChanged.connect(self._render)
        self.header.add_context_widget(self._context_field("INSPECT PLAYER", self.player_combo))

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
            if item.widget() is not None:
                item.widget().deleteLater()
            elif item.layout() is not None:
                OperationsConsole._clear_layout(item.layout())

    def refresh(self):
        try:
            self.roster = self.build_service.load()
        except Exception as exc:
            self.roster = BuildRoster()
            self.status.error(f"Failed to load builds: {exc}")

        current = self.player_combo.currentData()
        self.player_combo.blockSignals(True)
        self.player_combo.clear()
        for index, member in enumerate(self.roster.Members):
            name = member.Name or member.Gamertag or f"Player {index + 1}"
            label = f"{name} • {member.BuildName}" if member.BuildName else name
            self.player_combo.addItem(label, index)
        if current is not None:
            restored = self.player_combo.findData(current)
            if restored >= 0:
                self.player_combo.setCurrentIndex(restored)
        self.player_combo.blockSignals(False)
        self._render()

    def _selected_build(self) -> PlayerBuild | None:
        index = self.player_combo.currentData()
        if index is None:
            return self.roster.Members[0] if self.roster.Members else None
        try:
            return self.roster.Members[int(index)]
        except (IndexError, TypeError, ValueError):
            return None

    @staticmethod
    def _progression_for(build: PlayerBuild) -> CharacterProgression:
        return CharacterProgression(
            attributes=AttributeAllocation(
                health=int(getattr(build, "AttributeHealth", 0)),
                magicka=int(getattr(build, "AttributeMagicka", 0)),
                stamina=int(getattr(build, "AttributeStamina", 0)),
            )
        )

    @staticmethod
    def _build_text(build: PlayerBuild) -> str:
        values = list(build.FrontBarSkills) + list(build.BackBarSkills)
        values.extend([
            build.FrontBarWeapon.Set,
            build.BackBarWeapon.Set,
            *[entry.get("Set", "") for entry in build.Armor.values()],
        ])
        return " ".join(str(value or "") for value in values).lower()

    def _coverage(self):
        covered = {name: False for name in CORE_COVERAGE}
        providers = {name: [] for name in CORE_COVERAGE}
        for member in self.roster.Members:
            haystack = self._build_text(member)
            provider_name = member.Name or member.Gamertag or member.BuildName or "Unnamed"
            for capability in CORE_COVERAGE:
                aliases = EFFECT_ALIASES.get(capability, (capability.lower(),))
                if any(alias in haystack for alias in aliases):
                    covered[capability] = True
                    providers[capability].append(provider_name)
        return covered, providers

    def _render(self, *_args):
        self._clear_layout(self.layout)
        covered, providers = self._coverage()
        build = self._selected_build()

        top = QHBoxLayout()
        top.setSpacing(10)
        top.addWidget(self._raid_status_card(), 1)
        top.addWidget(self._coverage_card(covered, providers), 2)
        top.addWidget(self._warnings_card(covered), 1)
        top.addWidget(self._roster_card(), 1)
        self.layout.addLayout(top)

        middle = QHBoxLayout()
        middle.setSpacing(10)
        middle.addWidget(self._player_card(build), 2)
        middle.addWidget(self._provides_card(build), 1)
        middle.addWidget(self._gear_card(build), 1)
        middle.addWidget(self._key_stats_card(build), 1)
        self.layout.addLayout(middle)

        bottom = QHBoxLayout()
        bottom.setSpacing(10)
        bottom.addWidget(self._capability_gap_card(covered, providers), 1)
        bottom.addWidget(self._optimization_highlights_card(build), 1)
        bottom.addWidget(self._upcoming_mechanics_card(), 1)
        bottom.addWidget(self._raid_notes_card(), 1)
        self.layout.addLayout(bottom)
        self.layout.addStretch(1)

        self.status.info(
            f"Overview ready • {len(self.roster.Members)} saved build(s) • command-center layout active."
        )

    def _raid_status_card(self) -> FoundryCard:
        card = FoundryCard("Raid Status")
        tank_count = sum(1 for m in self.roster.Members if "tank" in str(m.Role or "").lower())
        healer_count = sum(1 for m in self.roster.Members if "heal" in str(m.Role or "").lower())
        dps_count = max(0, len(self.roster.Members) - tank_count - healer_count)
        for text in (
            f"✓  Tanks Ready   {tank_count}",
            f"✓  Healers Ready   {healer_count}",
            f"✓  DPS Ready   {dps_count}",
            "✓  Assignments Ready",
        ):
            card.addWidget(QLabel(text))
        card.addWidget(QLabel(f"{len(self.roster.Members)} saved players/builds"))
        return card

    def _coverage_card(self, covered, providers) -> FoundryCard:
        card = FoundryCard("Coverage Summary")
        grid = QGridLayout()
        for index, name in enumerate(CORE_COVERAGE):
            label = QLabel(f"{'✓' if covered[name] else '⚠'}  {name}")
            label.setProperty("overviewCoverageOk", bool(covered[name]))
            label.setToolTip(", ".join(providers[name]) if providers[name] else "No provider found")
            grid.addWidget(label, index % 5, index // 5)
        card.addLayout(grid)
        return card

    def _warnings_card(self, covered) -> FoundryCard:
        card = FoundryCard("Warnings")
        gaps = [name for name in CORE_COVERAGE if not covered[name]]
        if gaps:
            for name in gaps[:3]:
                card.addWidget(QLabel(f"⚠  {name} Missing"))
        else:
            card.addWidget(QLabel("✓  No core coverage gaps detected"))
        card.addWidget(QLabel("⚠  Penetration checks: placeholder"))
        card.addWidget(QLabel("⚠  Warhorn overlap: placeholder"))
        button = QPushButton(f"View All ({max(0, len(gaps) + 2)})")
        card.addWidget(button)
        return card

    def _roster_card(self) -> FoundryCard:
        card = FoundryCard(f"Raid Roster ({len(self.roster.Members)})")
        for member in self.roster.Members[:8]:
            name = member.Name or member.Gamertag or "Unnamed"
            role = member.Role or member.EsoClass or "Unassigned"
            card.addWidget(QLabel(f"✓  {name}\n     {role}"))
        if len(self.roster.Members) > 8:
            card.addWidget(QLabel(f"… and {len(self.roster.Members) - 8} more"))
        card.addWidget(QPushButton("View All Players"))
        return card

    def _player_card(self, build: PlayerBuild | None) -> FoundryCard:
        card = FoundryCard("Selected Player")
        if build is None:
            card.addWidget(QLabel("No saved build selected."))
            card.addStretch()
            return card
        name = build.Name or build.Gamertag or "Unnamed Player"
        title = QLabel(name.upper())
        title.setProperty("overviewPlayerName", True)
        card.addWidget(title)
        card.addWidget(QLabel(" • ".join(v for v in (build.EsoClass, build.Race, build.Role) if v)))
        for label, value in (
            ("HEALTH", getattr(build, "AttributeHealth", 0)),
            ("STAMINA", getattr(build, "AttributeStamina", 0)),
            ("MAGICKA", getattr(build, "AttributeMagicka", 0)),
        ):
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            bar = QProgressBar()
            bar.setRange(0, 64)
            bar.setValue(max(0, min(64, int(value or 0))))
            bar.setTextVisible(False)
            row.addWidget(bar, 1)
            row.addWidget(QLabel(str(value)))
            card.addLayout(row)
        card.addWidget(QLabel("QUICK LINKS"))
        card.addWidget(QLabel("⚔  View Full Build\n▥  Stat Breakdown\n☷  Buff/Debuff Uptime\n⚙  Optimization"))
        return card

    def _provides_card(self, build: PlayerBuild | None) -> FoundryCard:
        card = FoundryCard("Provides")
        if build is None:
            card.addWidget(QLabel("No build selected."))
            return card
        haystack = self._build_text(build)
        provided = []
        for capability in CORE_COVERAGE:
            aliases = EFFECT_ALIASES.get(capability, (capability.lower(),))
            if any(alias in haystack for alias in aliases):
                provided.append(capability)
        if not provided:
            card.addWidget(QLabel("No core coverage detected from saved names."))
        else:
            for item in provided[:7]:
                card.addWidget(QLabel(f"✓  {item}"))
        return card

    def _gear_card(self, build: PlayerBuild | None) -> FoundryCard:
        card = FoundryCard("Current Gear")
        if build is None:
            card.addWidget(QLabel("No build selected."))
            return card
        entries = []
        for slot in ("Head", "Shoulders", "Chest", "Hands", "Waist", "Legs", "Feet"):
            entry = build.Armor.get(slot, {})
            if entry.get("Set"):
                entries.append(entry["Set"])
        for slot in (build.FrontBarWeapon, build.BackBarWeapon, build.Necklace, build.Ring1, build.Ring2):
            if slot.Set:
                entries.append(slot.Set)
        unique = []
        for value in entries:
            if value not in unique:
                unique.append(value)
        card.addWidget(QLabel("\n".join(f"◇  {name}" for name in unique[:6]) or "No gear entered."))
        return card

    def _key_stats_card(self, build: PlayerBuild | None) -> FoundryCard:
        card = FoundryCard("Key Stats")
        if build is None:
            card.addWidget(QLabel("No build selected."))
            return card
        try:
            context = self.context_factory.build(
                character_id="overview-character",
                build_id="overview-build",
                build=build,
                progression=self._progression_for(build),
                active_bar="front",
            )
            stats = context.stats
            pairs = [
                ("Max Health", getattr(stats, "max_health", None)),
                ("Max Magicka", getattr(stats, "max_magicka", None)),
                ("Max Stamina", getattr(stats, "max_stamina", None)),
                ("Weapon Damage", getattr(stats, "weapon_damage", None)),
                ("Spell Damage", getattr(stats, "spell_damage", None)),
                ("Penetration", getattr(stats, "penetration", None)),
            ]
            text = "\n".join(f"{label}: {value:,}" if isinstance(value, (int, float)) else f"{label}: —" for label, value in pairs)
            card.addWidget(QLabel(text))
        except Exception:
            card.addWidget(QLabel("Calculated stats unavailable.\nThis card is ready for live values."))
        return card

    def _capability_gap_card(self, covered, providers) -> FoundryCard:
        card = FoundryCard("Capability Gap")
        gaps = [name for name in CORE_COVERAGE if not covered[name]]
        if gaps:
            card.addWidget(QLabel(f"⚠  {gaps[0].upper()}"))
            card.addWidget(QLabel("Not currently provided"))
            card.addWidget(QLabel("Recommended provider: placeholder"))
        else:
            card.addWidget(QLabel("✓  CORE COVERAGE COMPLETE"))
            card.addWidget(QLabel("No missing watch-list capability."))
        card.addWidget(QPushButton("View Options"))
        return card

    def _optimization_highlights_card(self, build: PlayerBuild | None) -> FoundryCard:
        card = FoundryCard("Optimization Highlights")
        card.addWidget(QLabel("Critical Damage     —   Target: encounter\nPenetration            —   Target: encounter\nUltimate Generation    —   Review"))
        card.addWidget(QPushButton("View Optimization"))
        return card

    def _upcoming_mechanics_card(self) -> FoundryCard:
        card = FoundryCard("Upcoming Mechanics")
        card.addWidget(QLabel("0:45   Portal Spawn\n1:15   Tank Swap\n1:30   Meteor Shower"))
        card.addWidget(QPushButton("View Full Timeline"))
        return card

    def _raid_notes_card(self) -> FoundryCard:
        card = FoundryCard("Raid Notes")
        card.setProperty("foundryNoteCard", True)
        notes = QLabel("• Watch portals on the east side\n• Don't cleave the shades\n• Save ults for execute\n• Call inc's early\n• Breathe. We got this.")
        notes.setProperty("noteCardBody", True)
        card.addWidget(notes)
        card.addWidget(QPushButton("Edit Notes"))
        return card
