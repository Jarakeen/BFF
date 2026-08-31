from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.components.foundry_card import FoundryCard
from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar
from ui.foundry_page import FoundryPage


class ReferenceDataPage(FoundryPage):
    """Fast combat dictionary for mechanics, attacks, effects, and death review."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entries = self._dummy_entries()
        self._build_ui()
        self._load_list()
        self._show_entry("Crushing Darkness")

    def _build_ui(self):
        self.header = FoundryHeader(
            title="Combat Reference",
            subtitle="Search mechanics, attacks, and status effects. Understand what they do and how to survive.",
            department="Raid Engine • Reference",
        )
        self.set_header(self.header)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search mechanics, attacks, or effects...")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._load_list)
        self.header.add_context_widget(self._context_field("SEARCH", self.search))

        self.trial_filter = QComboBox()
        self.trial_filter.addItems(["All Trials", "Cloudrest", "Lucent Citadel", "Dreadsail Reef", "Sunspire"])
        self.header.add_context_widget(self._context_field("FILTER BY", self.trial_filter))

        self.type_filter = QComboBox()
        self.type_filter.addItems(["All Types", "Attack", "Mechanic", "Status Effect", "Raid Damage"])
        self.header.add_context_widget(self._context_field("TYPE", self.type_filter))

        workspace = QHBoxLayout()
        workspace.setContentsMargins(0, 0, 0, 0)
        workspace.setSpacing(10)

        index_card = FoundryCard("Reference Index")
        self.results = QListWidget()
        self.results.currentTextChanged.connect(self._show_entry)
        index_card.addWidget(self.results)
        workspace.addWidget(index_card, 1)

        center = QVBoxLayout()
        center.setSpacing(10)
        self.entry_card = FoundryCard("Reference Entry")
        self.entry_name = QLabel()
        self.entry_name.setProperty("heroTitle", True)
        self.entry_summary = QLabel()
        self.entry_summary.setWordWrap(True)
        self.entry_details = QLabel()
        self.entry_details.setWordWrap(True)
        self.entry_details.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.entry_card.addWidget(self.entry_name)
        self.entry_card.addWidget(self.entry_summary)
        self.entry_card.addWidget(self.entry_details)
        self.entry_card.addStretch(1)
        center.addWidget(self.entry_card, 4)

        related = FoundryCard("Related Effects / Appears In")
        self.related_label = QLabel()
        self.related_label.setWordWrap(True)
        related.addWidget(self.related_label)
        center.addWidget(related, 1)
        workspace.addLayout(center, 3)

        right = QVBoxLayout()
        right.setSpacing(10)
        death = FoundryCard("Why Did We Die?")
        death.setProperty("parchment", True)
        self.death_label = QLabel()
        self.death_label.setWordWrap(True)
        death.addWidget(self.death_label)
        death.addWidget(QPushButton("Analyze Selected Death"))
        right.addWidget(death, 2)

        image = FoundryCard("Mechanic Visual")
        visual = QLabel("MECHANIC / ATTACK VISUAL\n\nArtwork, icon, combat-log sample,\nor positioning diagram can live here.")
        visual.setAlignment(Qt.AlignmentFlag.AlignCenter)
        visual.setMinimumHeight(260)
        visual.setProperty("bossArtworkPlaceholder", True)
        image.addWidget(visual)
        right.addWidget(image, 2)

        notes = FoundryCard("Field Notes")
        notes.setProperty("parchment", True)
        notes.addWidget(QLabel("Use this page during prog when somebody asks:\n\n'What was THAT?'\n\nThe answer should eventually be faster than opening six browser tabs and interrogating the dead person."))
        right.addWidget(notes, 1)
        workspace.addLayout(right, 2)

        host = QWidget()
        host.setLayout(workspace)
        self.add_workspace(host)
        self.status = FoundryStatusBar()
        self.set_status(self.status)
        self.status.info("Combat Reference ready • sample entries shown until encounter/reference data is wired in.")

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

    def _dummy_entries(self):
        return {
            "Crushing Darkness": {
                "tags": "EXECUTE • RAID DAMAGE • UNBLOCKABLE",
                "summary": "A dark void erupts under random players, dealing massive damage if the group fails to react.",
                "details": (
                    "Source: Z'Maja\nTrial: Cloudrest\nType: Execute / Raid Damage\nTarget: Random Players\n"
                    "Damage Type: Magic\nBlockable: No\nDodgeable: No\nInterruptible: No\nPurgeable: No\n"
                    "Mitigated By: resistance, shields, healing\nTrigger: encounter threshold\n"
                    "Failure Effect: heavy raid damage / deaths\nRecommended Response: spread, heal, shield, call early"
                ),
                "related": "Related: Major Maim • Major Defile • Twilight Tormentor\nAppears in: Cloudrest (Z'Maja)",
                "death": "DEATH ANALYSIS\nPlayer took lethal Magic Damage from Crushing Darkness.\n\nLIKELY CAUSE\nHit during an execute damage window without enough mitigation.\n\nNEXT TIME\nSpread, save shields/heals, and call the window early.",
            },
            "Heavy Attack": {
                "tags": "ATTACK • BLOCK CHECK",
                "summary": "A high-damage telegraphed attack commonly aimed at the tank or current aggro target.",
                "details": "Type: Direct Attack\nBlockable: Usually yes\nDodgeable: Encounter-dependent\nCommon Failure: missed block, debuff stack, wrong target\nRecommended Response: block or follow encounter-specific handling.",
                "related": "Related: taunt • block mitigation • tank swap",
                "death": "DEATH ANALYSIS\nIf a heavy attack killed someone, first check target, block state, debuff stacks, and whether the attack was meant to be shared or dodged.",
            },
            "Portal Spawn": {
                "tags": "MECHANIC • POSITIONING",
                "summary": "Encounter event that opens a portal or side-space and assigns players to leave the main arena.",
                "details": "Type: Mechanic\nFailure Risk: missed portal, wrong group, delayed return\nRecommended Response: pre-assign portal groups and backups.",
                "related": "Related: portal adds • group split • return timing",
                "death": "DEATH ANALYSIS\nPortal failures are usually assignment or timing failures rather than raw incoming damage. Check who was assigned and whether the spawn was called.",
            },
            "Minor Brittle": {
                "tags": "STATUS EFFECT • DEBUFF",
                "summary": "A target debuff used as part of group critical-damage optimization.",
                "details": "Type: Debuff\nUse: Group damage support\nPlanning Question: who provides it, from what source, and how reliably for this encounter?",
                "related": "Related: frost damage • critical damage • Coverage page",
                "death": "DEATH ANALYSIS\nMinor Brittle is not normally the thing that killed you. It may be the thing your optimizer is sulking about instead.",
            },
        }

    def _load_list(self, *_args):
        query = self.search.text().strip().lower() if hasattr(self, "search") else ""
        current = self.results.currentItem().text() if hasattr(self, "results") and self.results.currentItem() else ""
        self.results.blockSignals(True)
        self.results.clear()
        for name, entry in self._entries.items():
            haystack = f"{name} {entry['tags']} {entry['summary']}".lower()
            if not query or query in haystack:
                self.results.addItem(name)
        self.results.blockSignals(False)
        matches = self.results.findItems(current, Qt.MatchFlag.MatchExactly)
        if matches:
            self.results.setCurrentItem(matches[0])
        elif self.results.count():
            self.results.setCurrentRow(0)

    def _show_entry(self, name: str):
        if not name or name not in self._entries:
            return
        entry = self._entries[name]
        self.entry_card.set_title(entry["tags"])
        self.entry_name.setText(name.upper())
        self.entry_summary.setText(entry["summary"])
        self.entry_details.setText(entry["details"])
        self.related_label.setText(entry["related"])
        self.death_label.setText(entry["death"])
