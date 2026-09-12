from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
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
from services.accessibility_preferences import VISUAL_THEME_RYLO
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar
from ui.foundry_page import FoundryPage


CORE_COVERAGE = (
    "Major Courage",
    "Major Berserk",
    "Major Slayer",
    "Minor Force",
    "War Horn",
    "Major Vulnerability",
    "Major Breach",
    "Crusher",
    "Minor Maim",
    "Minor Brittle",
    "Orbs",
    "Magickasteal",
    "Minor Resolve",
    "Minor Intellect",
    "Purify",
)

EFFECT_ALIASES = {
    "War Horn": ("war horn", "aggressive horn"),
    "Orbs": ("orb", "necrotic orb", "energy orb", "shards"),
    "Crusher": ("crusher", "crushing"),
    "Magickasteal": ("magickasteal", "magicka steal", "restore magicka"),
    "Purify": ("purify", "purifying"),
    "Minor Brittle": ("minor brittle", "brittle"),
}


class OverviewRing(QWidget):
    """Small, deliberately restrained radial progress indicator for overview goals."""

    def __init__(
        self,
        percent: int,
        label: str,
        detail: str,
        *,
        accent: str = "#C8A46A",
        rylo_accent: str = "#AEB3B7",
        parent=None,
    ):
        super().__init__(parent)
        self.percent = max(0, min(100, int(percent)))
        self.label = label
        self.detail = detail
        self.accent = QColor(accent)
        self.rylo_accent = QColor(rylo_accent)
        self.setMinimumSize(112, 126)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        app = QApplication.instance()
        rylo = app is not None and app.property("visualTheme") == VISUAL_THEME_RYLO

        diameter = min(74, self.width() - 20)
        left = (self.width() - diameter) / 2
        ring = QRectF(left, 5, diameter, diameter)

        track = QColor("#414448" if rylo else "#24383A")
        cap = Qt.PenCapStyle.SquareCap if rylo else Qt.PenCapStyle.RoundCap
        accent = self.rylo_accent if rylo else self.accent
        painter.setPen(QPen(track, 7, Qt.PenStyle.SolidLine, cap))
        painter.drawArc(ring, 0, 360 * 16)

        painter.setPen(QPen(accent, 7, Qt.PenStyle.SolidLine, cap))
        painter.drawArc(ring, 90 * 16, -int(360 * 16 * self.percent / 100))

        painter.setPen(QColor("#E5ECEB"))
        font = painter.font()
        font.setPointSize(13)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(ring, Qt.AlignmentFlag.AlignCenter, f"{self.percent}%")

        font.setPointSize(9)
        font.setBold(False)
        painter.setFont(font)
        painter.setPen(QColor("#D5D6D7" if rylo else "#C8A46A"))
        painter.drawText(QRectF(0, 83, self.width(), 19), Qt.AlignmentFlag.AlignCenter, self.label)

        font.setPointSize(8)
        painter.setFont(font)
        painter.setPen(QColor("#C8CDD1" if rylo else "#BFC8C6"))
        painter.drawText(QRectF(0, 102, self.width(), 18), Qt.AlignmentFlag.AlignCenter, self.detail)
        painter.end()


class OperationsConsole(FoundryPage):
    """Planning-first Raid Engine overview and selected-character command dashboard."""

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
            subtitle="Plan. Prepare. Perform.",
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

        readiness = QWidget()
        readiness_layout = QVBoxLayout(readiness)
        readiness_layout.setContentsMargins(0, 0, 0, 0)
        readiness_layout.setSpacing(1)
        ready_heading = QLabel("PULL READINESS")
        ready_heading.setProperty("sidebarHeading", True)
        readiness_layout.addWidget(ready_heading)
        ready = QLabel("✓  READY")
        ready.setProperty("overviewReady", True)
        readiness_layout.addWidget(ready)
        readiness_layout.addWidget(QLabel("Planning checks available below"))
        self.header.add_context_widget(readiness)

        self.player_combo = QComboBox()
        self.player_combo.currentIndexChanged.connect(self._render)
        self.header.add_context_widget(self._context_field("INSPECT PLAYER", self.player_combo))

        self.workspace = QWidget()
        self.workspace.setProperty("operationsOverview", True)
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

        hero = QGridLayout()
        hero.setHorizontalSpacing(10)
        hero.setVerticalSpacing(10)
        hero.addWidget(self._player_card(build), 0, 0, 2, 2)
        hero.addWidget(self._raid_status_card(), 0, 2, 2, 1)
        hero.addWidget(self._coverage_card(covered, providers), 0, 3, 2, 2)
        hero.addWidget(self._warnings_card(covered), 0, 5, 2, 1)
        hero.setColumnStretch(0, 1)
        hero.setColumnStretch(1, 1)
        hero.setColumnStretch(2, 1)
        hero.setColumnStretch(3, 1)
        hero.setColumnStretch(4, 1)
        hero.setColumnStretch(5, 1)
        self.layout.addLayout(hero)

        details = QGridLayout()
        details.setHorizontalSpacing(10)
        details.setVerticalSpacing(10)
        details.addWidget(self._roster_card(), 0, 0, 1, 2)
        details.addWidget(self._provides_card(build), 0, 2, 1, 2)
        details.addWidget(self._gear_card(build), 0, 4, 1, 2)
        details.addWidget(self._key_stats_card(build), 0, 6, 1, 2)
        for column in range(8):
            details.setColumnStretch(column, 1)
        self.layout.addLayout(details)

        goals = QGridLayout()
        goals.setHorizontalSpacing(10)
        goals.setVerticalSpacing(10)
        goals.addWidget(self._achievements_card(), 0, 0, 1, 3)
        goals.addWidget(self._collectibles_card(), 0, 3, 1, 3)
        goals.addWidget(self._raid_schedule_card(build), 0, 6, 1, 2)
        goals.addWidget(self._skills_to_work_on_card(build), 0, 8, 1, 2)
        goals.addWidget(self._bookmarked_gear_card(), 0, 10, 1, 2)
        for column in range(12):
            goals.setColumnStretch(column, 1)
        self.layout.addLayout(goals)

        self.layout.addWidget(self._raid_notes_card())
        self.layout.addStretch(1)

        self.status.info(
            f"Overview ready • {len(self.roster.Members)} saved build(s) • planning dashboard active."
        )

    @staticmethod
    def _section_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setProperty("sidebarHeading", True)
        return label

    @staticmethod
    def _compact_button(text: str) -> QPushButton:
        button = QPushButton(text)
        button.setProperty("compactAction", True)
        return button

    @staticmethod
    def _progress_row(title: str, detail: str, value: int) -> QWidget:
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 1, 0, 1)
        layout.setSpacing(2)
        top = QHBoxLayout()
        name = QLabel(title)
        name.setProperty("overviewGoalName", True)
        top.addWidget(name)
        top.addStretch(1)
        top.addWidget(QLabel(f"{value}%"))
        layout.addLayout(top)
        subtitle = QLabel(detail)
        subtitle.setProperty("muted", True)
        layout.addWidget(subtitle)
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(value)
        bar.setTextVisible(False)
        bar.setFixedHeight(7)
        layout.addWidget(bar)
        return box

    def _raid_status_card(self) -> FoundryCard:
        card = FoundryCard("Raid Status")
        tank_count = sum(1 for m in self.roster.Members if "tank" in str(m.Role or "").lower())
        healer_count = sum(1 for m in self.roster.Members if "heal" in str(m.Role or "").lower())
        dps_count = max(0, len(self.roster.Members) - tank_count - healer_count)
        for text in (
            f"✓  Tanks Ready                 {tank_count}",
            f"✓  Healers Ready              {healer_count}",
            f"✓  DPS Ready                    {dps_count}",
            "✓  Assignments Ready",
        ):
            card.addWidget(QLabel(text))
        card.addStretch(1)
        ready = QLabel("✓   PULL READY")
        ready.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ready.setProperty("overviewReady", True)
        card.addWidget(ready)
        return card

    def _coverage_card(self, covered, providers) -> FoundryCard:
        card = FoundryCard("Coverage Summary")
        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(5)
        for index, name in enumerate(CORE_COVERAGE[:12]):
            label = QLabel(f"{'✓' if covered[name] else '⚠'}  {name}")
            label.setProperty("overviewCoverageOk", bool(covered[name]))
            label.setToolTip(", ".join(providers[name]) if providers[name] else "No provider found")
            grid.addWidget(label, index % 6, index // 6)
        card.addLayout(grid)
        card.addStretch(1)
        card.addWidget(self._compact_button(f"View Full Coverage ({len(CORE_COVERAGE)})"))
        return card

    def _warnings_card(self, covered) -> FoundryCard:
        card = FoundryCard("Warnings")
        gaps = [name for name in CORE_COVERAGE if not covered[name]]
        if gaps:
            for name in gaps[:4]:
                label = QLabel(f"⚠  {name} Missing\n     No source detected")
                label.setProperty("overviewWarning", True)
                card.addWidget(label)
        else:
            card.addWidget(QLabel("✓  No core coverage gaps detected"))
        card.addStretch(1)
        card.addWidget(self._compact_button("Open Coverage Checks"))
        return card

    def _roster_card(self) -> FoundryCard:
        card = FoundryCard(f"Raid Roster ({len(self.roster.Members)})")
        for member in self.roster.Members[:5]:
            name = member.Name or member.Gamertag or "Unnamed"
            role = member.Role or member.EsoClass or "Unassigned"
            build_name = member.BuildName or "Saved Build"
            card.addWidget(QLabel(f"●  {name:<18} {role}\n     {build_name}"))
        if len(self.roster.Members) > 5:
            card.addWidget(QLabel(f"… and {len(self.roster.Members) - 5} more"))
        card.addStretch(1)
        card.addWidget(self._compact_button("View All Players"))
        return card

    def _player_card(self, build: PlayerBuild | None) -> FoundryCard:
        card = FoundryCard("Character Command")
        card.setProperty("overviewAccent", "teal")
        if build is None:
            card.addWidget(QLabel("No saved build selected."))
            card.addStretch()
            return card

        heading = QHBoxLayout()
        identity = QVBoxLayout()
        name = build.Name or build.Gamertag or "Unnamed Player"
        title = QLabel(name.upper())
        title.setProperty("overviewPlayerName", True)
        identity.addWidget(title)
        identity.addWidget(QLabel(" • ".join(v for v in (build.EsoClass, build.Race, build.Role) if v)))
        heading.addLayout(identity, 1)
        build_name = QLabel(build.BuildName or "Saved Build")
        build_name.setProperty("cardBadge", True)
        heading.addWidget(build_name, 0, Qt.AlignmentFlag.AlignTop)
        card.addLayout(heading)

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

        actions = QHBoxLayout()
        for text in ("Build", "Stats", "Buff Uptime", "Optimization"):
            actions.addWidget(self._compact_button(text))
        card.addLayout(actions)
        return card

    def _provides_card(self, build: PlayerBuild | None) -> FoundryCard:
        title = "Provides"
        if build is not None and build.BuildName:
            title = f"Provides ({build.BuildName})"
        card = FoundryCard(title)
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
            for item in provided[:6]:
                card.addWidget(QLabel(f"✓  {item}"))
        card.addStretch(1)
        card.addWidget(self._compact_button("View Full Breakdown"))
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
        card.addStretch(1)
        card.addWidget(self._compact_button("View Gear & Set Details"))
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
                ("Maximum Health", getattr(stats, "max_health", None)),
                ("Maximum Magicka", getattr(stats, "max_magicka", None)),
                ("Maximum Stamina", getattr(stats, "max_stamina", None)),
                ("Weapon Damage", getattr(stats, "weapon_damage", None)),
                ("Spell Damage", getattr(stats, "spell_damage", None)),
                ("Penetration", getattr(stats, "penetration", None)),
            ]
            grid = QGridLayout()
            for row, (label, value) in enumerate(pairs):
                grid.addWidget(QLabel(label), row, 0)
                rendered = f"{value:,.0f}" if isinstance(value, (int, float)) else "—"
                number = QLabel(rendered)
                number.setAlignment(Qt.AlignmentFlag.AlignRight)
                grid.addWidget(number, row, 1)
            card.addLayout(grid)
        except Exception:
            card.addWidget(QLabel("Calculated stats unavailable.\nSaved-build values will appear when resolvable."))
        return card

    def _achievements_card(self) -> FoundryCard:
        card = FoundryCard("Achievements Close")
        card.setWatermark = getattr(card, "set_watermark", None)
        if callable(card.setWatermark):
            card.setWatermark("feather", 0.04)
        for title, detail, value in (
            ("Godslayer", "One requirement remaining", 93),
            ("Gryphon Heart", "Closing in on completion", 82),
            ("Swashbuckler Supreme", "Dreadsail Reef progress", 80),
            ("Voice of Reason", "Rockgrove progress", 80),
        ):
            card.addWidget(self._progress_row(title, detail, value))
        card.addWidget(self._compact_button("View All Achievements"))
        return card

    def _collectibles_card(self) -> FoundryCard:
        card = FoundryCard("Collectibles Focus")
        card.setProperty("overviewAccent", "teal")
        rings = QHBoxLayout()
        rings.setSpacing(4)
        rings.addWidget(OverviewRing(68, "Sticker Book", "412 / 605", accent="#C8A46A"))
        rings.addWidget(OverviewRing(42, "Mounts", "18 / 43", accent="#59AEB3", rylo_accent="#88BDE9"))
        card.addLayout(rings)
        card.addWidget(self._section_label("PRIORITY GOALS"))
        grid = QGridLayout()
        goals = (
            ("Sunspire Skin", "0 / 1"),
            ("DSR Mount", "0 / 1"),
            ("Trial Pet Fragment", "2 / 3"),
            ("Class Style (Warden)", "4 / 5"),
        )
        for row, (name, progress) in enumerate(goals):
            grid.addWidget(QLabel(f"◇  {name}"), row, 0)
            value = QLabel(progress)
            value.setAlignment(Qt.AlignmentFlag.AlignRight)
            grid.addWidget(value, row, 1)
        card.addLayout(grid)
        return card

    def _raid_schedule_card(self, build: PlayerBuild | None) -> FoundryCard:
        card = FoundryCard("Raid Schedule")
        card.addWidget(self._section_label("NEXT RAIDS"))
        role = (build.Role if build is not None else None) or "Role TBD"
        build_name = (build.BuildName if build is not None else None) or "Build TBD"
        entries = (
            ("MON", "Sunspire HM", "19:00", role),
            ("WED", "Dreadsail Reef", "19:00", role),
            ("FRI", "Rockgrove Prog", "19:00", build_name),
            ("SUN", "AS L+M", "18:00", role),
        )
        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        for row, (day, raid, time, assignment) in enumerate(entries):
            grid.addWidget(QLabel(day), row, 0)
            grid.addWidget(QLabel(f"{raid}\n{time}"), row, 1)
            assigned = QLabel(assignment)
            assigned.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            grid.addWidget(assigned, row, 2)
        card.addLayout(grid)
        card.addStretch(1)
        card.addWidget(self._compact_button("Open Calendar"))
        return card

    def _skills_to_work_on_card(self, build: PlayerBuild | None) -> FoundryCard:
        card = FoundryCard("Skills to Work On")
        class_name = (build.EsoClass if build is not None else None) or "your build"
        for title, detail in (
            ("Minor Brittle uptime", f"Keep {class_name} coverage deliberate"),
            ("War Horn timing", "Align with group burst windows"),
            ("Orb cadence", "Keep placement consistent"),
            ("Bar swap consistency", "Reduce avoidable downtime"),
            ("Resource management", "Avoid unnecessary overcapping"),
        ):
            label = QLabel(f"○  {title}\n     {detail}")
            label.setWordWrap(True)
            card.addWidget(label)
        card.addStretch(1)
        card.addWidget(self._compact_button("Open Performance Focus"))
        return card

    def _bookmarked_gear_card(self) -> FoundryCard:
        card = FoundryCard("Bookmarked Gear")
        for name, note in (
            ("Spell Power Cure", "Healer support"),
            ("Pillager's Profit", "Group utility"),
            ("Roaring Opportunist", "Raid support"),
            ("Pearls of Ehlnofey", "Sustain / ultimate"),
            ("Jorvuld's Guidance", "Effect duration"),
        ):
            row = QLabel(f"☆  {name}\n     {note}")
            card.addWidget(row)
        card.addStretch(1)
        card.addWidget(self._compact_button("Manage Bookmarks"))
        return card

    # Legacy helpers remain available for compatibility with older page patches/tests,
    # but they are intentionally no longer part of the planning-first layout.
    def _capability_gap_card(self, covered, providers) -> FoundryCard:
        card = FoundryCard("Capability Gap")
        gaps = [name for name in CORE_COVERAGE if not covered[name]]
        if gaps:
            card.addWidget(QLabel(f"⚠  {gaps[0].upper()}"))
            card.addWidget(QLabel("Not currently provided"))
        else:
            card.addWidget(QLabel("✓  CORE COVERAGE COMPLETE"))
        return card

    def _optimization_highlights_card(self, build: PlayerBuild | None) -> FoundryCard:
        card = FoundryCard("Optimization Highlights")
        card.addWidget(QLabel("Optimization details live on the dedicated Optimization page."))
        return card

    def _upcoming_mechanics_card(self) -> FoundryCard:
        card = FoundryCard("Encounter Planning")
        card.addWidget(QLabel("Moment-by-moment mechanics are intentionally kept off this overview."))
        return card

    def _raid_notes_card(self) -> FoundryCard:
        card = FoundryCard("Raid Notes")
        card.setProperty("foundryNoteCard", True)
        notes = QLabel(
            "Watch portals on the east side.     Don't cleave the shades.     "
            "Save ults for execute.     Call inc's early.     Breathe. We got this."
        )
        notes.setWordWrap(True)
        notes.setProperty("noteCardBody", True)
        card.addWidget(notes)
        return card
