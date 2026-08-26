from __future__ import annotations

from collections import Counter
from pathlib import Path

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
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


# These are deliberately the first raid-lead watch list rather than a claim
# that these are every useful ESO effect. The underlying data model can grow
# beyond this dashboard without changing the page structure.
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


class CoverageBarChart(QFrame):
    """Small Foundry-native bar chart for group capability coverage."""

    def __init__(self, values: list[tuple[str, int]], parent=None):
        super().__init__(parent)
        self.values = values
        self.setMinimumHeight(205)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setProperty("coverageChart", True)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#0d0f0f"))

        if not self.values:
            painter.setPen(QColor("#9b9b92"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No coverage data")
            painter.end()
            return

        left = 150
        right = 30
        top = 22
        row_h = 30
        bar_h = 12
        width = max(100, self.width() - left - right)

        painter.setFont(QFont("Segoe UI", 9))
        for index, (label, value) in enumerate(self.values):
            y = top + index * row_h
            painter.setPen(QColor("#c7c2b8"))
            painter.drawText(0, y, left - 12, row_h, Qt.AlignmentFlag.AlignVCenter, label)

            track = QRectF(left, y + (row_h - bar_h) / 2, width, bar_h)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#252a28"))
            painter.drawRoundedRect(track, 5, 5)

            pct = max(0, min(100, int(value)))
            fill = QRectF(left, y + (row_h - bar_h) / 2, width * pct / 100.0, bar_h)
            fill_color = QColor("#76a68d") if pct >= 80 else QColor("#c39a55") if pct >= 50 else QColor("#9c5d4f")
            painter.setBrush(fill_color)
            painter.drawRoundedRect(fill, 5, 5)

            painter.setPen(QColor("#d7d1c4"))
            painter.drawText(
                left + width + 8,
                y,
                40,
                row_h,
                Qt.AlignmentFlag.AlignVCenter,
                f"{pct}%",
            )

        painter.end()


class CoverageItem(QFrame):
    """Compact check/warning item used by the raid-lead coverage board."""

    def __init__(self, name: str, covered: bool, provider_count: int, parent=None):
        super().__init__(parent)
        self.setProperty("coverageItem", True)
        self.setProperty("covered", covered)
        self.setMinimumHeight(42)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 5, 8, 5)
        layout.setSpacing(8)

        icon = QLabel("✓" if covered else "!")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setFixedSize(25, 25)
        icon.setStyleSheet(
            "border-radius: 12px; font-weight: 700; font-size: 13px; "
            + ("background:#173d3b; color:#9ed4c8; border:1px solid #4f9487;"
               if covered else
               "background:#4a321b; color:#e4a84f; border:1px solid #b47b31;")
        )
        layout.addWidget(icon)

        text = QLabel(name)
        text.setProperty("coverageName", True)
        layout.addWidget(text, 1)

        provider = QLabel(
            f"{provider_count} provider" + ("" if provider_count == 1 else "s")
        )
        provider.setProperty("coverageProvider", True)
        layout.addWidget(provider)


class OptimizationPage(FoundryPage):
    """Raid-lead optimization desk: coverage first, optimization second."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.data_dir = Path(__file__).resolve().parents[1] / "data"
        self.database = EsoDatabase(self.data_dir / "eso.db")
        self.reference = ReferenceDataService(self.database)
        self.build_service = BuildService(self.data_dir / "builds.json")
        self.roster = BuildRoster()
        self.mock_lab = MockRosterLab()
        self._skill_index: dict[str, dict] | None = None

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
        try:
            rows = self.database.execute(
                """
                SELECT name FROM content
                WHERE content_type = 'trial' AND TRIM(name) != ''
                ORDER BY name COLLATE NOCASE
                """
            ).fetchall()
            return [row["name"] for row in rows] or ["Current Trial"]
        except Exception:
            return ["Current Trial"]

    @staticmethod
    def _clear_layout(layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
                continue
            nested = item.layout()
            if nested is not None:
                OptimizationPage._clear_layout(nested)
                nested.setParent(None)
                nested.deleteLater()

    def refresh(self, *_args):
        try:
            self.roster = self.build_service.load()
        except Exception as exc:
            self.roster = BuildRoster()
            self.status.error(f"Failed to load builds: {exc}")

        self._clear_layout(self.layout)
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
                f"Planning from {len(self.roster.Members)} saved build(s). Coverage is roster-derived, not log uptime."
            )

    # ------------------------------------------------------------------
    # Coverage command center
    # ------------------------------------------------------------------

    def _render_coverage(self):
        coverage, providers = self._resolve_core_coverage()
        covered_count = sum(1 for name in CORE_COVERAGE if coverage.get(name))
        total = len(CORE_COVERAGE)
        score = round(covered_count / total * 100) if total else 0
        gaps = [name for name in CORE_COVERAGE if not coverage.get(name)]
        overlaps = sorted(
            ((name, len(providers.get(name, []))) for name in CORE_COVERAGE if len(providers.get(name, [])) > 1),
            key=lambda item: item[1],
            reverse=True,
        )

        overview = FoundryCard("Group Coverage", "◈")
        overview.set_badge(f"{covered_count}/{total} COVERED")
        overview.addWidget(QLabel(
            "Raid-lead coverage from the current roster. A check means at least one equipped build is a potential provider; it does not claim encounter uptime."
        ))

        metrics = QHBoxLayout()
        metrics.setSpacing(10)
        for label, value, detail in (
            ("COVERAGE", f"{score}%", "core watch list"),
            ("PROVIDERS", str(sum(len(v) for v in providers.values())), "resolved sources"),
            ("GAPS", str(len(gaps)), "not represented"),
            ("OVERLAP", str(len(overlaps)), "multiple providers"),
        ):
            metrics.addWidget(self._metric(label, value, detail), 1)
        overview.addLayout(metrics)
        self.layout.addWidget(overview)

        coverage_card = FoundryCard("Coverage Summary", "✓")
        coverage_card.set_badge("GROUP")
        grid = QGridLayout()
        grid.setHorizontalSpacing(22)
        grid.setVerticalSpacing(5)
        columns = 3
        rows = (total + columns - 1) // columns
        for index, name in enumerate(CORE_COVERAGE):
            column = index // rows
            row = index % rows
            grid.addWidget(
                CoverageItem(name, coverage[name], len(providers.get(name, []))),
                row,
                column,
            )
        coverage_card.addLayout(grid)
        self.layout.addWidget(coverage_card)

        lower = QHBoxLayout()
        lower.setSpacing(10)

        chart_card = FoundryCard("Coverage by Category", "▥")
        chart_values = self._category_scores(coverage)
        chart_card.addWidget(CoverageBarChart(chart_values))
        chart_card.addWidget(QLabel(
            "Category scores are a compact planning view of the 15-item watch list. They will become encounter-weighted once requirements are connected."
        ))
        lower.addWidget(chart_card, 2)

        attention = FoundryCard("Raid Lead Attention", "!")
        attention.set_badge("NEXT")
        if gaps:
            attention.addWidget(self._section_label("COVERAGE GAPS"))
            for name in gaps[:5]:
                attention.addWidget(self._attention_row("!", name, "No provider found in saved builds."))
        else:
            attention.addWidget(self._attention_row("✓", "Core coverage complete", "Every watch-list effect has a roster provider."))
        if overlaps:
            attention.addWidget(self._section_label("REDUNDANCY"))
            for name, count in overlaps[:3]:
                attention.addWidget(self._attention_row("+", name, f"{count} potential providers."))
        lower.addWidget(attention, 1)
        self.layout.addLayout(lower)

        assignments = FoundryCard("Provider Map", "⌁")
        assignments.set_badge("WHO CARRIES WHAT")
        table = QTableWidget(0, 3)
        table.setHorizontalHeaderLabels(["CAPABILITY", "PROVIDER", "SOURCE"])
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)
        table.setMinimumHeight(220)
        for name in CORE_COVERAGE:
            source_rows = providers.get(name, [])
            if not source_rows:
                source_rows = [("—", "Not represented")]
            for provider_name, source in source_rows[:3]:
                row = table.rowCount()
                table.insertRow(row)
                table.setItem(row, 0, QTableWidgetItem(name))
                table.setItem(row, 1, QTableWidgetItem(provider_name))
                table.setItem(row, 2, QTableWidgetItem(source))
        assignments.addWidget(table)
        self.layout.addWidget(assignments)

        note = FoundryCard("What This Means", "i")
        note.addWidget(QLabel(
            "This desk currently answers: what does the roster appear capable of providing? "
            "The next optimization layer will answer: which provider should carry each responsibility, and what changes improve total coverage?"
        ))
        self.layout.addWidget(note)
        self.layout.addStretch(1)

    def _metric(self, label: str, value: str, detail: str) -> QFrame:
        frame = QFrame()
        frame.setProperty("optimizationMetric", True)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(1)
        small = QLabel(label)
        small.setProperty("sidebarHeading", True)
        big = QLabel(value)
        big.setStyleSheet("font-size: 23px; font-weight: 700; color: #d5b06a;")
        sub = QLabel(detail)
        sub.setStyleSheet("color: #8f918a; font-size: 11px;")
        layout.addWidget(small)
        layout.addWidget(big)
        layout.addWidget(sub)
        return frame

    def _section_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setProperty("sidebarHeading", True)
        return label

    def _attention_row(self, icon: str, title: str, body: str) -> QFrame:
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(8, 5, 8, 5)
        layout.setSpacing(1)
        head = QLabel(f"{icon}  {title}")
        head.setStyleSheet("font-weight: 600; color: #d6d0c3;")
        detail = QLabel(body)
        detail.setWordWrap(True)
        detail.setStyleSheet("color: #92948d; font-size: 11px;")
        layout.addWidget(head)
        layout.addWidget(detail)
        return frame

    @staticmethod
    def _category_scores(coverage: dict[str, bool]) -> list[tuple[str, int]]:
        groups = {
            "Major buffs": ["Major Courage", "Major Berserk", "Major Slayer"],
            "Debuffs": ["Major Vulnerability", "Major Breach", "Crusher", "Minor Maim", "Minor Brittle"],
            "Group utility": ["War Horn", "Orbs", "Magickasteal", "Purify"],
            "Defensive": ["Minor Resolve", "Minor Intellect"],
            "Offensive": ["Minor Force"],
        }
        result = []
        for label, names in groups.items():
            result.append((label, round(sum(coverage.get(name, False) for name in names) / len(names) * 100)))
        return result

    def _resolve_core_coverage(self):
        coverage = {name: False for name in CORE_COVERAGE}
        providers: dict[str, list[tuple[str, str]]] = {name: [] for name in CORE_COVERAGE}
        skill_index = self._get_skill_index()

        for build in self.roster.Members:
            player = build.Name or build.Gamertag or "Unnamed"
            set_names = self._set_names(build)
            set_watches = self.reference.suggest_watches_for_sets(set_names)
            for capability in CORE_COVERAGE:
                aliases = (capability.casefold(),) + tuple(EFFECT_ALIASES.get(capability, ()))
                if any(self._matches_aliases(watch, aliases) for watch in set_watches):
                    coverage[capability] = True
                    providers[capability].append((player, "Gear / set signal"))

                for skill_name in list(build.FrontBarSkills) + list(build.BackBarSkills):
                    record = skill_index.get(skill_name.strip().casefold())
                    if not record:
                        continue
                    searchable = f"{record.get('name', '')} {record.get('description', '')}"
                    if any(self._matches_aliases(searchable, aliases) for aliases in [aliases]):
                        coverage[capability] = True
                        providers[capability].append((player, f"Skill: {record.get('name', skill_name)}"))

        for capability in providers:
            seen = set()
            providers[capability] = [
                row for row in providers[capability]
                if not (row in seen or seen.add(row))
            ]
        return coverage, providers

    @staticmethod
    def _matches_aliases(text: str, aliases) -> bool:
        haystack = str(text).casefold()
        return any(alias.casefold() in haystack for alias in aliases)

    def _get_skill_index(self) -> dict[str, dict]:
        if self._skill_index is None:
            self._skill_index = {}
            try:
                for row in self.reference.list_skills():
                    name = str(row.get("name", "")).strip()
                    if name:
                        self._skill_index.setdefault(name.casefold(), row)
            except Exception:
                pass
        return self._skill_index

    # ------------------------------------------------------------------
    # Secondary views
    # ------------------------------------------------------------------

    def _render_suggestions(self):
        intro = FoundryCard("Comp Engine Suggestions", "◇")
        intro.addWidget(QLabel("Build hygiene and obvious roster gaps. These suggestions do not pretend to be encounter optimization yet."))
        self.layout.addWidget(intro)
        suggestions = []
        for build in self.roster.Members:
            name = build.Name or build.Gamertag or "Unnamed"
            missing = [slot for slot, value in self._gear_rows(build) if not value]
            if missing:
                suggestions.append(("Gear completion", f"{name}: finish {', '.join(missing[:3])}."))
            if not build.ChampionPoints:
                suggestions.append(("Champion Points", f"{name}: configure CP before optimization."))
            skills = sum(1 for skill in build.FrontBarSkills + build.BackBarSkills if skill.strip())
            if skills < 12:
                suggestions.append(("Skill coverage", f"{name}: {skills}/12 skill slots configured."))
        if not suggestions:
            suggestions = [("No immediate build gaps", "The saved builds have basic equipment, CP, and skill data configured."),
                           ("Next layer", "Use Coverage to inspect group capability before assigning responsibilities.")]
        for title, body in suggestions[:12]:
            card = FoundryCard(title)
            card.addWidget(QLabel(body))
            self.layout.addWidget(card)
        self.layout.addStretch(1)

    def _render_assignments(self):
        card = FoundryCard("Assignment Optimization", "⌁")
        card.addWidget(QLabel("This is the next decision layer: provider assignment belongs here, not in the Builds editor."))
        card.addWidget(QLabel("The current Coverage view already resolves potential providers from saved gear and skills. The optimizer can build on that map without changing the roster."))
        card.addWidget(QLabel("Future output: recommended provider, competing providers, conflicts, and before/after coverage."))
        self.layout.addWidget(card)
        self.layout.addStretch(1)

    # ------------------------------------------------------------------
    # Test Lab retained as the disposable simulation surface
    # ------------------------------------------------------------------

    def _render_test_lab(self):
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(10)

        banner = FoundryCard("SIMULATION • Encounter Test Lab")
        banner.addWidget(QLabel("Build a disposable roster, evaluate it, and deliberately try to break the MinMax assumptions."))
        banner.addWidget(QLabel("Nothing here changes Builds, roster assignments, ESO Logs data, or the production database."))
        page_layout.addWidget(banner)

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
        page_layout.addLayout(top_row)

        preset_panel = self._build_preset_lab(scenario_combo, scenarios, scenario_description, evaluate_button)
        custom_widget = CustomRosterLabWidget()
        preset_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        custom_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        stack = QStackedWidget()
        stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        stack.addWidget(preset_panel)
        stack.addWidget(custom_widget)
        page_layout.addWidget(stack, 1)

        def update_mode(index: int):
            is_preset = index == 0
            scenario_label.setText("SCENARIO" if is_preset else "ROSTER")
            scenario_card.setVisible(is_preset)
            scenario_combo.setVisible(is_preset)
            evaluate_button.setVisible(is_preset)
            scenario_description.setText(
                scenarios[scenario_combo.currentIndex()].description
                if is_preset else
                "Custom Roster • disposable evidence/build sandbox. Use the roster editor below to add players, gear, and skills."
            )
            stack.setCurrentIndex(index)

        mode_combo.currentIndexChanged.connect(update_mode)
        stack.currentChanged.connect(lambda index: self.status.info(
            "SIMULATION ONLY — custom roster is disposable." if index == 1
            else "SIMULATION ONLY — preset mock roster data is disposable."
        ))
        update_mode(mode_combo.currentIndex())
        self.layout.addWidget(page, 1)

    def _build_preset_lab(self, scenario_combo, scenarios, description, evaluate_button) -> QWidget:
        panel = QWidget()
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(10)

        roster_card = FoundryCard("Mock Roster Members")
        roster_table = QTableWidget(0, 3)
        roster_table.setHorizontalHeaderLabels(["Player", "Role", "Capabilities"])
        roster_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        roster_table.horizontalHeader().setStretchLastSection(True)
        roster_card.addWidget(roster_table)
        panel_layout.addWidget(roster_card)

        results_card = FoundryCard("Encounter Evaluation")
        results_table = QTableWidget(0, 5)
        results_table.setHorizontalHeaderLabels(["Requirement", "Result", "Valid", "Required", "Explanation"])
        results_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
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
                roster_table.setItem(row_index, 2, QTableWidgetItem(", ".join(player.capabilities) or "None"))

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

    # ------------------------------------------------------------------
    # Build helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _set_names(build) -> list[str]:
        names = []
        for slot in list(build.Armor.values()) + [build.Necklace, build.Ring1, build.Ring2, build.FrontBarWeapon, build.BackBarWeapon]:
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
        for label, value in [("Neck", build.Necklace), ("Ring 1", build.Ring1), ("Ring 2", build.Ring2), ("Main Hand", build.FrontBarWeapon), ("Off Hand", build.BackBarWeapon)]:
            rows.append((label, value.Set.strip()))
        return rows
