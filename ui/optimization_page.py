from __future__ import annotations

from collections import Counter
from pathlib import Path

from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from minmax.mock_roster_lab import MockRosterLab
from models.build_model import BuildRoster
from services.build_service import BuildService
from services.eso_database import EsoDatabase
from services.reference_data_service import ReferenceDataService
from ui.components.custom_roster_lab import CustomRosterLabWidget
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar
from ui.foundry_page import FoundryPage


class OptimizationPage(FoundryPage):
    """Optimization Desk with disposable Phase 5 testing surfaces."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.data_dir = Path(__file__).resolve().parents[1] / "data"
        self.database = EsoDatabase(self.data_dir / "eso.db")
        self.reference = ReferenceDataService(self.database)
        self.build_service = BuildService(self.data_dir / "builds.json")
        self.roster = BuildRoster()
        self.mock_lab = MockRosterLab()

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
        self.view_combo.addItems(["Coverage", "Suggestions", "Assignments", "Test Lab"])
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
        """Return actual trial content only, not dungeons or arenas."""
        try:
            rows = self.database.execute(
                """
                SELECT name
                FROM content
                WHERE content_type = 'trial'
                  AND TRIM(name) != ''
                ORDER BY name COLLATE NOCASE
                """
            ).fetchall()
            return [row["name"] for row in rows] or ["Current Trial"]
        except Exception:
            return ["Current Trial"]

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
        elif view == "Test Lab":
            self._render_test_lab()
        else:
            self._render_coverage()

        if view == "Test Lab":
            self.status.info("SIMULATION ONLY — mock roster data is not saved to your real roster.")
        else:
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
            "Phase 4 encounter evaluation is now available through the Test Lab as a safe simulation surface."
        ))
        note.addWidget(QLabel(
            "Production Builds and ESO Logs remain outside the simulation path."
        ))
        self.layout.addWidget(note)
        self.layout.addStretch(1)

    def _render_test_lab(self):
        banner = FoundryCard("SIMULATION • Encounter Test Lab")
        banner.addWidget(QLabel(
            "Build a disposable roster, evaluate it, and deliberately try to break the MinMax assumptions."
        ))
        banner.addWidget(QLabel(
            "Nothing here changes Builds, roster assignments, ESO Logs data, or the production database."
        ))
        self.layout.addWidget(banner)

        mode_card = FoundryCard("Test Mode")
        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("MODE"))
        mode_combo = QComboBox()
        mode_combo.addItems(["Preset Scenarios", "Custom Roster"])
        mode_row.addWidget(mode_combo, 1)
        mode_card.addLayout(mode_row)

        scenario_card = FoundryCard("Roster / Scenario")
        scenario_row = QHBoxLayout()
        scenario_label = QLabel("SCENARIO")
        scenario_combo = QComboBox()
        scenarios = self.mock_lab.scenarios()
        scenario_combo.addItems([scenario.name for scenario in scenarios])
        evaluate_button = QPushButton("Evaluate")
        scenario_row.addWidget(scenario_label)
        scenario_row.addWidget(scenario_combo, 1)
        scenario_row.addWidget(evaluate_button)
        scenario_card.addLayout(scenario_row)
        scenario_description = QLabel()
        scenario_description.setWordWrap(True)
        scenario_card.addWidget(scenario_description)

        top_row = QHBoxLayout()
        top_row.setSpacing(10)
        top_row.addWidget(mode_card, 1)
        top_row.addWidget(scenario_card, 1)
        self.layout.addLayout(top_row)

        preset_panel = self._build_preset_lab(
            scenario_combo,
            scenarios,
            scenario_description,
            evaluate_button,
        )
        custom_widget = CustomRosterLabWidget()

        stack = QStackedWidget()
        stack.addWidget(preset_panel)
        stack.addWidget(custom_widget)
        stack.currentChanged.connect(
            lambda index: self.status.info(
                "SIMULATION ONLY — custom roster is disposable."
                if index == 1
                else "SIMULATION ONLY — preset mock roster data is disposable."
            )
        )
        mode_combo.currentIndexChanged.connect(stack.setCurrentIndex)
        self.layout.addWidget(stack, 1)

        def update_mode(index: int):
            is_preset = index == 0
            scenario_card.setVisible(is_preset)
            if is_preset:
                scenario_description.setText(scenarios[scenario_combo.currentIndex()].description)

        mode_combo.currentIndexChanged.connect(update_mode)
        update_mode(0)

    def _build_preset_lab(
        self,
        scenario_combo: QComboBox,
        scenarios,
        description: QLabel,
        evaluate_button: QPushButton,
    ) -> QWidget:
        panel = QWidget()
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(10)

        roster_card = FoundryCard("Mock Roster Members")
        roster_table = QTableWidget(0, 3)
        roster_table.setHorizontalHeaderLabels(["Player", "Role", "Capabilities"])
        roster_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        roster_table.horizontalHeader().setStretchLastSection(True)
        roster_card.addWidget(roster_table)
        panel_layout.addWidget(roster_card)

        results_card = FoundryCard("Encounter Evaluation")
        results_table = QTableWidget(0, 5)
        results_table.setHorizontalHeaderLabels(
            ["Requirement", "Result", "Valid", "Required", "Explanation"]
        )
        results_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        results_table.horizontalHeader().setStretchLastSection(True)
        results_card.addWidget(results_table)
        panel_layout.addWidget(results_card)

        def run_evaluation():
            scenario = scenarios[scenario_combo.currentIndex()]
            description.setText(scenario.description)
            roster_table.setRowCount(len(scenario.players))

            for row_index, player in enumerate(scenario.players):
                roster_table.setItem(row_index, 0, QTableWidgetItem(player.name))
                roster_table.setItem(row_index, 1, QTableWidgetItem(player.role.value.upper()))
                roster_table.setItem(
                    row_index,
                    2,
                    QTableWidgetItem(", ".join(player.capabilities) or "None"),
                )

            evaluation = self.mock_lab.evaluate(scenario)
            results_table.setRowCount(len(evaluation.classifications))

            for row_index, result in enumerate(evaluation.classifications):
                results_table.setItem(row_index, 0, QTableWidgetItem(result.effect_name))
                results_table.setItem(row_index, 1, QTableWidgetItem(result.classification.value.upper()))
                results_table.setItem(row_index, 2, QTableWidgetItem(str(result.valid_provider_count)))
                results_table.setItem(row_index, 3, QTableWidgetItem(str(result.required_provider_count)))
                results_table.setItem(row_index, 4, QTableWidgetItem(result.explanation))

            problems = len(evaluation.problems)
            state = "READY" if evaluation.is_fully_covered else f"{problems} PROBLEM(S)"
            self.status.info(f"SIMULATION: {scenario.name} • {state}")

        scenario_combo.currentIndexChanged.connect(run_evaluation)
        evaluate_button.clicked.connect(run_evaluation)
        run_evaluation()

        panel_layout.addStretch(1)
        return panel

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
