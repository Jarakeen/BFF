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
from services.raid_coverage_profile import DEFAULT_RAID_COVERAGE_PROFILE
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar
from ui.foundry_page import FoundryPage


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
    """Buff/debuff planning desk. Planned coverage now, observed uptime later."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.build_service = BuildService(get_data_dir() / "builds.json")
        self.roster = BuildRoster()
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        self.header = FoundryHeader(
            title="Coverage & Buff Management",
            subtitle="Track required buffs and debuffs. Know what's covered, what's missing, and by whom.",
            department="Raid Engine • Coverage",
        )
        self.set_header(self.header)

        self.encounter_combo = QComboBox()
        self.encounter_combo.addItems(["Current Encounter", "Whole Trial", "Custom Plan"])
        self.header.add_context_widget(self._context_field("VIEW", self.encounter_combo))

        self.tabs = QTabWidget()
        self.tabs.addTab(self._coverage_tab(), "BUFFS & DEBUFFS")
        self.tabs.addTab(self._placeholder("Providers", "Provider reliability and substitutions will live here."), "PROVIDERS")
        self.tabs.addTab(self._placeholder("Uptime Analysis", "Combat-log uptime comparison will live here when imported logs are connected."), "UPTIME ANALYSIS")
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
