from __future__ import annotations

from collections import Counter
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from models.build_model import BuildRoster
from services.build_service import BuildService
from services.eso_database import EsoDatabase
from services.reference_data_service import ReferenceDataService
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar
from ui.foundry_page import FoundryPage


class OptimizationPage(FoundryPage):
    """
    Optimization Desk.

    This is intentionally independent of ESO Logs. It uses the saved Builds
    roster as planning evidence and provides the surface where the MinMax
    encounter evaluator can be connected next.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.data_dir = Path(__file__).resolve().parents[1] / "data"
        self.database = EsoDatabase(self.data_dir / "eso.db")
        self.reference = ReferenceDataService(self.database)
        self.build_service = BuildService(self.data_dir / "builds.json")
        self.roster = BuildRoster()

        self._build_ui()
        self.refresh()

    def _build_ui(self):
        self.header = FoundryHeader(
            title="Optimization",
            subtitle="Turn build data into group-level decisions.",
            department="Raid Operations",
        )
        self.set_header(self.header)

        self.trial_combo = QComboBox()
        self.trial_combo.addItems(self._list_trials())
        self.trial_combo.currentTextChanged.connect(self.refresh)
        self.header.add_context_widget(self._context_field("TRIAL", self.trial_combo))

        self.view_combo = QComboBox()
        self.view_combo.addItems(["Coverage", "Suggestions", "Assignments"])
        self.view_combo.currentTextChanged.connect(self.refresh)
        self.header.add_context_widget(self._context_field("VIEW", self.view_combo))

        self.workspace = QWidget()
        self.layout = QVBoxLayout(self.workspace)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(10)
        self.add_workspace(self.workspace)

        self.status = FoundryStatusBar()
        self.set_status(self.status)

    def _context_field(self, title: str, widget: QWidget) -> QWidget:
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        label = QLabel(title)
        label.setProperty("sidebarHeading", True)
        layout.addWidget(label)
        layout.addWidget(widget)
        return box

    def _list_trials(self) -> list[str]:
        try:
            rows = self.database.execute(
                """
                SELECT DISTINCT content_name
                FROM bosses
                WHERE content_name IS NOT NULL
                  AND TRIM(content_name) != ''
                ORDER BY content_name COLLATE NOCASE
                """
            ).fetchall()
            return [row["content_name"] for row in rows] or ["Current Raid"]
        except Exception:
            return ["Current Raid"]

    def refresh(self, *_args):
        try:
            self.roster = self.build_service.load()
        except Exception as exc:
            self.roster = BuildRoster()
            self.status.error(f"Failed to load builds: {exc}")

        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        view = self.view_combo.currentText()
        if view == "Suggestions":
            self._render_suggestions()
        elif view == "Assignments":
            self._render_assignments()
        else:
            self._render_coverage()

        self.status.info(
            f"Planning from {len(self.roster.Members)} saved build(s). ESO Logs are not used on this page."
        )

    def _render_coverage(self):
        intro = FoundryCard("Group Coverage")
        intro.addWidget(QLabel(
            "Build-derived coverage signals. These are planning hints from equipped sets, not encounter results yet."
        ))
        self.layout.addWidget(intro)

        coverage = Counter()
        sources: dict[str, list[str]] = {}
        for build in self.roster.Members:
            sets = self._set_names(build)
            for watch in self.reference.suggest_watches_for_sets(sets):
                key = watch.casefold()
                coverage[key] += 1
                sources.setdefault(key, []).append(build.Name or build.Gamertag or "Unnamed")

        if not coverage:
            card = FoundryCard("No Signals")
            card.addWidget(QLabel("Equip sets on the Builds page to populate planning signals."))
            self.layout.addWidget(card)
            return

        card = FoundryCard("Current Planning Signals")
        for key, count in coverage.most_common(20):
            row = QHBoxLayout()
            row.addWidget(QLabel(key.title()))
            row.addStretch()
            row.addWidget(QLabel(f"{count} source(s)"))
            names = ", ".join(sources.get(key, [])[:4])
            row.addWidget(QLabel(names))
            card.addLayout(row)
        self.layout.addWidget(card)

        note = FoundryCard("MinMax Evaluation")
        note.addWidget(QLabel(
            "Phase 4 encounter evaluation is the next mechanical connection: requirements → coverage → gaps/conflicts → classification."
        ))
        note.addWidget(QLabel(
            "This page is deliberately ready for that engine without pulling combat-log data into Builds."
        ))
        self.layout.addWidget(note)
        self.layout.addStretch(1)

    def _render_suggestions(self):
        card = FoundryCard("Comp Engine Suggestions")
        suggestions = []
        for build in self.roster.Members:
            name = build.Name or build.Gamertag or "Unnamed"
            missing = [slot for slot, value in self._gear_rows(build) if not value]
            if missing:
                suggestions.append(("Gear completion", f"{name}: finish {', '.join(missing[:3])}."))
            if not build.ChampionPoints:
                suggestions.append(("Champion Points", f"{name}: configure CP before optimization."))
            skills = sum(1 for s in build.FrontBarSkills + build.BackBarSkills if s.strip())
            if skills < 12:
                suggestions.append(("Skill coverage", f"{name}: {skills}/12 skill slots configured."))

        if not suggestions:
            suggestions = [
                ("No immediate build gaps", "The saved builds have basic equipment, CP, and skill data configured."),
                ("Next connection", "Feed EncounterEvaluation results into this desk for real group recommendations."),
            ]

        for title, body in suggestions[:12]:
            row = FoundryCard(title)
            row.addWidget(QLabel(body))
            self.layout.addWidget(row)
        self.layout.addStretch(1)

    def _render_assignments(self):
        card = FoundryCard("Assignment Optimization")
        card.addWidget(QLabel(
            "Provider assignment belongs here, not in the Builds editor."
        ))
        card.addWidget(QLabel(
            "The next implementation step is to feed classified encounter requirements into this surface and show who should carry each responsibility."
        ))
        card.addWidget(QLabel(
            "No ESO Logs dependency is introduced here."
        ))
        self.layout.addWidget(card)
        self.layout.addStretch(1)

    @staticmethod
    def _set_names(build) -> list[str]:
        names = []
        for slot in list(build.Armor.values()) + [
            build.Necklace,
            build.Ring1,
            build.Ring2,
            build.FrontBarWeapon,
            build.BackBarWeapon,
        ]:
            if hasattr(slot, "Set"):
                name = slot.Set.strip()
            else:
                name = str(slot.get("Set", "")).strip()
            if name:
                names.append(name)
        return names

    @staticmethod
    def _gear_rows(build):
        rows = []
        for slot, value in build.Armor.items():
            set_name = value.get("Set", "") if isinstance(value, dict) else value.Set
            rows.append((slot, set_name.strip()))
        for label, value in [
            ("Neck", build.Necklace),
            ("Ring 1", build.Ring1),
            ("Ring 2", build.Ring2),
            ("Main Hand", build.FrontBarWeapon),
            ("Off Hand", build.BackBarWeapon),
        ]:
            rows.append((label, value.Set.strip()))
        return rows
