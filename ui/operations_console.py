from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, QTimer
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
from minmax.stat_ids import StatId
from models.build_model import BuildRoster, PlayerBuild
from services.build_service import BuildService
from services.saved_build_capability_service import SavedBuildCapabilityService, summarize_raid_coverage
from services.raid_coverage_profile import DEFAULT_RAID_COVERAGE_PROFILE
from services.expedition_service import ExpeditionService
from services.accessibility_preferences import VISUAL_THEME_RYLO
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar
from ui.foundry_page import FoundryPage


CORE_COVERAGE = tuple(
    row.display_name for row in DEFAULT_RAID_COVERAGE_PROFILE.requirements if row.required
)


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
        self.capability_service = None
        self._capability_audits = {}
        self._build_ui()
        self.refresh()
        # MainWindow attaches its sibling pages after this constructor returns.
        QTimer.singleShot(0, self._refresh_when_attached)

    def _refresh_when_attached(self):
        if isinstance(getattr(self.window(), "pages", None), dict):
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
        self.trial_label = QLabel(f"{trial}{f' ({difficulty})' if difficulty else ''}")
        encounter_layout.addWidget(self.trial_label)
        self.boss_label = QLabel(boss)
        self.boss_label.setProperty("overviewEncounterName", True)
        encounter_layout.addWidget(self.boss_label)
        self.header.add_context_widget(encounter_box)

        readiness = QWidget()
        readiness_layout = QVBoxLayout(readiness)
        readiness_layout.setContentsMargins(0, 0, 0, 0)
        readiness_layout.setSpacing(1)
        ready_heading = QLabel("BUILD READINESS")
        ready_heading.setProperty("sidebarHeading", True)
        readiness_layout.addWidget(ready_heading)
        self.pull_readiness_label = QLabel("—  NOT VERIFIED")
        self.pull_readiness_label.setProperty("overviewWarning", True)
        readiness_layout.addWidget(self.pull_readiness_label)
        self.readiness_hint = QLabel("Set on Builds page")
        readiness_layout.addWidget(self.readiness_hint)
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
        self._refresh_encounter_context()
        try:
            self.roster = self.build_service.load()
        except Exception as exc:
            self.roster = BuildRoster()
            self.status.error(f"Failed to load builds: {exc}")

        current = self.player_combo.currentData()
        self.player_combo.blockSignals(True)
        self.player_combo.clear()
        for index, member in enumerate(self.roster.Members):
            if not ((member.Name or member.Gamertag or member.BuildName or "").strip()):
                continue
            name = member.Name or member.Gamertag or f"Player {index + 1}"
            label = f"{name} • {member.BuildName}" if member.BuildName else name
            self.player_combo.addItem(label, index)
        if current is not None:
            restored = self.player_combo.findData(current)
            if restored >= 0:
                self.player_combo.setCurrentIndex(restored)
        self.player_combo.blockSignals(False)
        self._render()

    def _refresh_encounter_context(self):
        expedition = self.expedition.expedition
        trial = expedition.Expedition or "No Active Expedition"
        difficulty = expedition.Difficulty or ""
        self.trial_label.setText(f"{trial}{f' ({difficulty})' if difficulty else ''}")
        self.boss_label.setText(expedition.Objective or "No Encounter Selected")

    def _selected_build(self) -> PlayerBuild | None:
        index = self.player_combo.currentData()
        if index is None:
            return self._saved_builds()[0] if self._saved_builds() else None
        try:
            return self.roster.Members[int(index)]
        except (IndexError, TypeError, ValueError):
            return None

    def _saved_builds(self) -> tuple[PlayerBuild, ...]:
        return tuple(
            build for build in self.roster.Members
            if (build.Name or "").strip() or (build.Gamertag or "").strip()
            or (build.BuildName or "").strip()
        )

    @staticmethod
    def _progression_for(build: PlayerBuild) -> CharacterProgression:
        return CharacterProgression(
            attributes=AttributeAllocation(
                health=int(getattr(build, "AttributeHealth", 0)),
                magicka=int(getattr(build, "AttributeMagicka", 0)),
                stamina=int(getattr(build, "AttributeStamina", 0)),
            )
        )

    def _coverage(self):
        """Report proven static availability, never encounter uptime or pull readiness."""
        profile = DEFAULT_RAID_COVERAGE_PROFILE
        empty = summarize_raid_coverage(profile, [])
        self._capability_audits = {}
        builds = self._saved_builds()
        if not builds or not DEFAULT_DATABASE.is_file():
            return empty.status, empty.providers
        try:
            if self.capability_service is None:
                self.capability_service = SavedBuildCapabilityService(self.build_service, DEFAULT_DATABASE)
            for build in builds:
                self._capability_audits[id(build)] = self.capability_service.audit_build(build)
        except Exception as exc:
            self._capability_audits = {}
            self.status.warning(f"Saved-build coverage could not be audited: {exc}")
            return empty.status, empty.providers
        snapshot = summarize_raid_coverage(
            profile, [(build, self._capability_audits[id(build)]) for build in builds]
        )
        return snapshot.status, snapshot.providers

    def _render(self, *_args):
        self._clear_layout(self.layout)
        covered, providers = self._coverage()
        build = self._selected_build()
        confirmed = bool(build and build.ReadyForRaid)
        self.pull_readiness_label.setText("✓  READY" if confirmed else "—  NOT MARKED READY")
        self.readiness_hint.setText("Set on Builds page" if build else "Choose a saved build")
        self.pull_readiness_label.setProperty("overviewReady", confirmed)
        self.pull_readiness_label.setProperty("overviewWarning", not confirmed)
        self.pull_readiness_label.style().unpolish(self.pull_readiness_label)
        self.pull_readiness_label.style().polish(self.pull_readiness_label)

        self._hero_cards = (
            self._player_card(build), self._raid_status_card(),
            self._coverage_card(covered, providers), self._warnings_card(covered),
        )
        self._detail_cards = (
            self._roster_card(), self._provides_card(build),
            self._gear_card(build), self._key_stats_card(build),
        )
        self._goal_cards = (
            self._achievements_card(), self._collectibles_card(),
            self._raid_schedule_card(build), self._skills_to_work_on_card(build),
        )
        self._hero_grid = QGridLayout()
        self._detail_grid = QGridLayout()
        self._goal_grid = QGridLayout()
        for grid in (self._hero_grid, self._detail_grid, self._goal_grid):
            grid.setHorizontalSpacing(10)
            grid.setVerticalSpacing(10)
        self._arrange_overview_grid(self._hero_grid, self._hero_cards, (
            (0, 0, 1, 1), (0, 1, 1, 1), (0, 2, 1, 1), (0, 3, 1, 1),
        ), 4)
        self._arrange_overview_grid(self._detail_grid, self._detail_cards, (
            (0, 0, 1, 1), (0, 1, 1, 1), (0, 2, 1, 1), (0, 3, 1, 1),
        ), 4)
        self._arrange_overview_grid(self._goal_grid, self._goal_cards, (
            (0, 0, 1, 1), (0, 1, 1, 1), (0, 2, 1, 1), (0, 3, 1, 1),
        ), 4)
        self.layout.addLayout(self._hero_grid)
        self.layout.addLayout(self._detail_grid)
        self.layout.addLayout(self._goal_grid)

        self.layout.addWidget(self._raid_notes_card())
        self.layout.addStretch(1)
        self.workspace_widget.updateGeometry()

        self.status.info(
            f"Overview loaded • {len(self._saved_builds())} saved build(s) • planning dashboard active."
        )

    @staticmethod
    def _arrange_overview_grid(grid, cards, positions, columns):
        while grid.count():
            grid.takeAt(0)
        for column in range(columns):
            grid.setColumnStretch(column, 1)
        for card, position in zip(cards, positions):
            grid.addWidget(card, *position)

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
        build = self._selected_build()
        if build is None:
            card.addWidget(QLabel("No saved build selected."))
        else:
            card.addWidget(QLabel(f"Selected: {build.Name or build.BuildName or 'Unnamed build'}"))
            card.addWidget(QLabel("Ready" if build.ReadyForRaid else "Not marked ready"))
        builds = self._saved_builds()
        card.addWidget(QLabel(f"Ready saved builds: {sum(member.ReadyForRaid for member in builds)} / {len(builds)}"))
        card.addStretch(1)
        ready = QLabel("Set readiness on Builds page")
        ready.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ready.setProperty("overviewWarning", True)
        card.addWidget(ready)
        return card

    def _coverage_card(self, covered, providers) -> FoundryCard:
        card = FoundryCard("Coverage Evidence")
        grid = QGridLayout()
        grid.setVerticalSpacing(5)
        identified = [name for name in CORE_COVERAGE if covered.get(name) != "unverified"]
        for index, name in enumerate(identified[:6]):
            state = covered.get(name, "unverified")
            marker = "✓" if state == "available" else "◇" if state == "conditional" else "?"
            label = QLabel(f"{marker}  {name}")
            label.setProperty("overviewCoverageOk", state == "available")
            explanation = {
                "available": "Static capability on saved build (uptime unverified): " + ", ".join(providers[name]),
                "conditional": "Conditional static source; activation and uptime unverified",
                "not_found": "No mapped source identified in audited saved builds",
                "unverified": "No supported source mapping or audit available",
            }
            label.setToolTip(explanation[state])
            grid.addWidget(label, index, 0)
        if identified:
            card.addLayout(grid)
            if len(identified) > 6:
                more = QLabel(f"+ {len(identified) - 6} more identified checks in Coverage")
                more.setWordWrap(True)
                card.addWidget(more)
        else:
            empty = QLabel("No saved-build coverage effect verified yet.")
            empty.setWordWrap(True)
            card.addWidget(empty)
        unknown_count = sum(state == "unverified" for state in covered.values())
        if unknown_count:
            unknown = QLabel(f"{unknown_count} effects unverified • inspect source gaps in Coverage")
            unknown.setWordWrap(True)
            card.addWidget(unknown)
        card.addStretch(1)
        coverage_link = self._compact_button("View Coverage Details")
        coverage_link.setToolTip("See the same saved-build capability evidence in the Coverage plan; assignments and uptime are not inferred.")
        card.addWidget(coverage_link)
        return card

    def _warnings_card(self, covered) -> FoundryCard:
        card = FoundryCard("Planning Checks")
        gaps = [name for name, state in covered.items() if state in {"not_found", "conditional"}]
        if gaps:
            for name in gaps[:4]:
                label = QLabel(f"?  {name}\n     {covered[name].replace('_', ' ').title()}")
                label.setProperty("overviewWarning", True)
                card.addWidget(label)
        elif any(state == "unverified" for state in covered.values()):
            message = QLabel("Coverage evidence incomplete.\nReview unresolved sources in Coverage.")
            message.setWordWrap(True)
            card.addWidget(message)
        else:
            card.addWidget(QLabel("Static sources identified; uptime not checked."))
        card.addStretch(1)
        coverage_link = self._compact_button("Open Coverage Checks")
        coverage_link.setToolTip("See the same saved-build capability evidence in the Coverage plan; assignments and uptime are not inferred.")
        card.addWidget(coverage_link)
        return card

    def _roster_card(self) -> FoundryCard:
        builds = self._saved_builds()
        card = FoundryCard(f"Saved Builds ({len(builds)})")
        for member in builds[:5]:
            name = member.Name or member.Gamertag or "Unnamed"
            role = member.Role or member.EsoClass or "Unassigned"
            build_name = member.BuildName or "Saved Build"
            member_label = QLabel(f"●  {name} · {role}\n     {build_name}")
            member_label.setWordWrap(True)
            card.addWidget(member_label)
        if len(builds) > 5:
            card.addWidget(QLabel(f"… and {len(builds) - 5} more"))
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

        name = build.Name or build.Gamertag or "Unnamed Player"
        title = QLabel(name.upper())
        title.setProperty("overviewPlayerName", True)
        title.setWordWrap(True)
        card.addWidget(title)
        identity = QLabel(" • ".join(v for v in (build.EsoClass, build.Race, build.Role) if v))
        identity.setWordWrap(True)
        card.addWidget(identity)
        build_name = QLabel(build.BuildName or "Saved Build")
        build_name.setProperty("cardBadge", True)
        build_name.setWordWrap(True)
        card.addWidget(build_name)

        for label, value in (
            ("HEALTH", getattr(build, "AttributeHealth", 0)),
            ("STAMINA", getattr(build, "AttributeStamina", 0)),
            ("MAGICKA", getattr(build, "AttributeMagicka", 0)),
        ):
            row = QHBoxLayout()
            row.setSpacing(6)
            name_label = QLabel(label.title())
            name_label.setFixedWidth(66)
            row.addWidget(name_label)
            bar = QProgressBar()
            bar.setRange(0, 64)
            bar.setValue(max(0, min(64, int(value or 0))))
            bar.setTextVisible(False)
            bar.setProperty("overviewAttribute", label.lower())
            bar.setFixedSize(96, 12)
            row.addWidget(bar)
            amount = QLabel(str(value))
            amount.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            amount.setFixedWidth(20)
            row.addWidget(amount)
            row.addStretch(1)
            card.addLayout(row)

        actions = QGridLayout()
        actions.setHorizontalSpacing(6)
        actions.setVerticalSpacing(6)
        for index, text in enumerate(("Build", "Stats", "Buff Uptime", "Optimization")):
            actions.addWidget(self._compact_button(text), index // 2, index % 2)
        card.addLayout(actions)
        return card

    def _provides_card(self, build: PlayerBuild | None) -> FoundryCard:
        card = FoundryCard("Build Evidence")
        if build is None:
            card.addWidget(QLabel("No build selected."))
            return card
        if build.BuildName:
            build_label = QLabel(build.BuildName)
            build_label.setWordWrap(True)
            card.addWidget(build_label)
        audit = self._capability_audits.get(id(build))
        if audit is None:
            message = QLabel("Canonical saved-build evidence unavailable.")
            message.setWordWrap(True)
            card.addWidget(message)
        else:
            matched = []
            for row in DEFAULT_RAID_COVERAGE_PROFILE.mapped_required:
                if row.requirement_id == "war_horn":
                    continue
                for effect in audit.resolved_effects:
                    if effect.name == row.capability_type:
                        marker = "◇" if effect.condition or effect.trigger else "✓"
                        matched.append(f"{marker}  {row.display_name}")
                        break
            for item in matched[:6]:
                card.addWidget(QLabel(item))
            if not matched:
                message = QLabel("No mapped static source identified on this build.")
                message.setWordWrap(True)
                card.addWidget(message)
            if audit.capability_unresolved:
                unresolved = QLabel(f"?  {len(audit.capability_unresolved)} unresolved source(s) • hover for details")
                unresolved.setToolTip("\n".join(audit.capability_unresolved))
                card.addWidget(unresolved)
            card.addWidget(QLabel("Availability only • uptime not checked"))
        card.addStretch(1)
        card.addWidget(self._compact_button("View Full Breakdown"))
        return card

    def _gear_card(self, build: PlayerBuild | None) -> FoundryCard:
        card = FoundryCard("Gear & Bookmarks")
        if build is None:
            card.addWidget(QLabel("No build selected."))
        else:
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
            card.addWidget(self._section_label("EQUIPPED SETS"))
            card.addWidget(QLabel("\n".join(f"◇  {name}" for name in unique[:4]) or "No gear entered."))
        card.addWidget(self._section_label("BOOKMARKS"))
        self._add_bookmarked_gear_content(card, limit=3)
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
            resources = context.character_state
            derived = context.core_state.derived if context.core_state else {}
            pairs = [
                ("Maximum Health", resources.max_health),
                ("Maximum Magicka", resources.max_magicka),
                ("Maximum Stamina", resources.max_stamina),
                ("Weapon Damage", getattr(derived.get(StatId.WEAPON_DAMAGE), "final_value", None)),
                ("Spell Damage", getattr(derived.get(StatId.SPELL_DAMAGE), "final_value", None)),
                ("Physical Penetration", getattr(derived.get(StatId.PHYSICAL_PENETRATION), "final_value", None)),
                ("Spell Penetration", getattr(derived.get(StatId.SPELL_PENETRATION), "final_value", None)),
            ]
            grid = QGridLayout()
            for row, (label, value) in enumerate(pairs):
                grid.addWidget(QLabel(label), row, 0)
                rendered = f"{value:,.0f}" if isinstance(value, (int, float)) else "—"
                number = QLabel(rendered)
                number.setAlignment(Qt.AlignmentFlag.AlignRight)
                grid.addWidget(number, row, 1)
            card.addLayout(grid)
            note = QLabel("Static front-bar snapshot • no combat uptime")
            note.setWordWrap(True)
            card.addWidget(note)
            if context.unresolved_gear_effects:
                card.addWidget(QLabel(f"?  {len(context.unresolved_gear_effects)} gear effect(s) unresolved"))
        except Exception as exc:
            message = QLabel("Calculated stats unavailable; check the saved build and reference data.")
            message.setWordWrap(True)
            card.addWidget(message)
            card.setToolTip(str(exc))
        return card

    def _achievements_card(self) -> FoundryCard:
        card = FoundryCard("Achievement Progress")
        card.set_watermark("feather", 0.04)
        page = getattr(self.window(), "pages", {}).get("achievements")
        stats = getattr(page, "achievement_stats_service", None)
        progress = getattr(page, "achievement_progress_service", None)
        if stats is None or progress is None:
            card.addWidget(QLabel("Achievement progress is not loaded yet."))
        else:
            try:
                progress.reload(preserve_active_profile=True)
                profile = progress.active_profile
                card.addWidget(QLabel(f"Profile: {profile} • completed achievements"))
                categories = {name.casefold(): name for name in stats.top_categories()}
                for title, values in (
                    ("All Achievements", stats.overall()),
                    *((name, stats.category(categories[name.casefold()])) for name in ("Trials", "Dungeons") if name.casefold() in categories),
                ):
                    earned, total = values["count_earned"], values["count_total"]
                    if total:
                        card.addWidget(self._progress_row(title, f"{earned} / {total} completed", round(100 * earned / total)))
            except Exception as exc:
                card.addWidget(QLabel(f"Saved achievement progress unavailable: {exc}"))
        card.addWidget(self._compact_button("View All Achievements"))
        return card

    def _collectibles_card(self) -> FoundryCard:
        card = FoundryCard("Collectibles Focus")
        card.setProperty("overviewAccent", "teal")
        window = self.window()
        collectible_service = getattr(window, "collectible_service", None)
        sticker_page = getattr(window, "pages", {}).get("stickerbook")
        sticker_service = getattr(sticker_page, "service", None)
        sticker_profile = getattr(sticker_page, "profile_id", "Default")
        rings_data = []
        try:
            if sticker_service is not None:
                owned, total = sticker_service.summary(sticker_profile)
                if total:
                    rings_data.append((owned, total, "Sticker Book", sticker_profile, "#C8A46A", "#AEB3B7"))
            if collectible_service is not None:
                owned, total = collectible_service.progress_summary("Mounts")
                if total:
                    rings_data.append((owned, total, "Mounts", collectible_service.active_profile, "#59AEB3", "#88BDE9"))
        except Exception as exc:
            card.addWidget(QLabel(f"Collection progress unavailable: {exc}"))
            rings_data.clear()
        rings = QHBoxLayout()
        rings.setSpacing(4)
        for owned, total, title, profile, accent, rylo_accent in rings_data:
            rings.addWidget(OverviewRing(round(100 * owned / total), title, f"{owned} / {total}", accent=accent, rylo_accent=rylo_accent))
        if rings_data:
            card.addLayout(rings)
            profiles = ", ".join(f"{title}: {profile}" for _, _, title, profile, _, _ in rings_data)
            card.addWidget(QLabel(f"Profiles • {profiles}"))
        else:
            card.addWidget(QLabel("No saved collection totals available yet."))
        card.addStretch(1)
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
        grid.setColumnStretch(1, 2)
        grid.setColumnStretch(2, 1)
        for row, (day, raid, time, assignment) in enumerate(entries):
            grid.addWidget(QLabel(day), row, 0)
            grid.addWidget(QLabel(f"{raid}\n{time}"), row, 1)
            assigned = QLabel(assignment)
            assigned.setWordWrap(True)
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
        self._add_bookmarked_gear_content(card, limit=5)
        card.addStretch(1)
        card.addWidget(self._compact_button("Manage Bookmarks"))
        return card

    def _add_bookmarked_gear_content(self, card: FoundryCard, *, limit: int) -> None:
        gear_page = getattr(self.window(), "pages", {}).get("gear_lookup")
        service = getattr(gear_page, "gear_bookmark_service", None)
        profile_combo = getattr(gear_page, "gear_bookmark_profile", None)
        profile = profile_combo.currentText().strip() if profile_combo is not None else "Default"
        profile = profile or "Default"
        if service is None:
            message = QLabel("Saved set bookmarks are not loaded yet.")
            message.setWordWrap(True)
            card.addWidget(message)
        else:
            try:
                bookmarked = service.bookmarked_set_ids(profile)
                names = {row.get("gear_set_id"): row.get("name") for row in gear_page._sets}
                card.addWidget(QLabel(f"Profile: {profile}"))
                for set_id in sorted(bookmarked, key=lambda value: str(names.get(value) or value).casefold())[:limit]:
                    name = names.get(set_id) or f"Set #{set_id} (catalog name unavailable)"
                    note = service.note(profile, set_id)
                    card.addWidget(QLabel(f"☆  {name}" + (f"\n     {note}" if note else "")))
                if not bookmarked:
                    card.addWidget(QLabel("No sets bookmarked for this profile."))
                elif len(bookmarked) > limit:
                    card.addWidget(QLabel(f"+ {len(bookmarked) - limit} more saved set(s)"))
            except Exception as exc:
                card.addWidget(QLabel(f"Bookmarks unavailable: {exc}"))

    # Legacy helpers remain available for compatibility with older page patches/tests,
    # but they are intentionally no longer part of the planning-first layout.
    def _capability_gap_card(self, covered, providers) -> FoundryCard:
        card = FoundryCard("Capability Gap")
        gaps = [name for name in CORE_COVERAGE if covered.get(name) != "available"]
        if gaps:
            card.addWidget(QLabel(f"⚠  {gaps[0].upper()}"))
            card.addWidget(QLabel("Not verified in saved-build evidence"))
        else:
            card.addWidget(QLabel("Static sources found; uptime not checked"))
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
