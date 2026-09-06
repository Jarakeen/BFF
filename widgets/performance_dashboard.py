# widgets/performance_dashboard.py
#
# One raid team member's Performance Dashboard tab: point it at an
# ESO Logs report/fight, pick which player in that fight is you
# (by name, or by an anonymized label like "Anonymous 7" when the
# report owner hid names), and see your own buff/debuff uptime plus
# your healing or damage output as charts instead of a raw table --
# role-aware, so a healer sees their healing output and a DPS sees
# theirs, both against the same uptime picture.
#
# Holds no network/DB access of its own -- the page owns
# PerformanceDashboardService and calls into this widget's public
# API, same convention as widgets/capability_editor.py.

from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QMargins
from PySide6.QtGui import QColor
from PySide6.QtCharts import (
    QBarCategoryAxis,
    QBarSeries,
    QBarSet,
    QChart,
    QChartView,
    QHorizontalBarSeries,
    QLineSeries,
    QValueAxis,
)
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from ui.components.foundry_button import ButtonRole, FoundryButton
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_empty_state import FoundryEmptyState
from ui.theme.colors import Colors
from ui.theme.fonts import Fonts

from models.performance_model import ActorChoice, PerformanceProfile, PerformanceSnapshot

# Role picker options, plus the accent color each role's charts use
# so a healer's tab and a DPS's tab read as visually distinct at a
# glance, matching the role colors already used elsewhere (rosters,
# status badges) via ui.theme.colors.Colors.ROLE.
ROLE_OPTIONS = ["Healer", "DPS", "Tank"]


class _StatBlock(QWidget):
    """One KPI callout -- a big value over a small caption."""

    def __init__(self, caption: str, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(2)

        self.value_label = QLabel("--")
        self.value_label.setFont(Fonts.statistic())
        self.value_label.setStyleSheet(f"color: {Colors.GOLD_LIGHT};")
        self.value_label.setWordWrap(True)

        caption_label = QLabel(caption)
        caption_label.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 11px;")

        layout.addWidget(self.value_label)
        layout.addWidget(caption_label)

    def set_value(self, text: str):
        self.value_label.setText(text)


def _new_chart() -> QChart:

    chart = QChart()
    chart.setBackgroundBrush(QColor(Colors.SURFACE))
    chart.setBackgroundRoundness(0)
    chart.legend().hide()
    chart.setMargins(QMargins(6, 6, 6, 6))
    chart.setTitleBrush(QColor(Colors.TEXT_MUTED))

    return chart


def _empty_chart(message: str) -> QChart:

    chart = _new_chart()
    chart.setTitle(message)

    return chart


class PerformanceDashboard(QWidget):

    nameChanged = Signal(str)

    loadFightRequested = Signal()
    showPerformanceRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self._actor_choices: list[ActorChoice] = []
        self._last_profile = PerformanceProfile()
        self._last_snapshot: PerformanceSnapshot | None = None

        self.build_ui()

    # --------------------------------------------------
    # UI
    # --------------------------------------------------

    def build_ui(self):

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        root.addWidget(self._build_source_card())

        self.kpi_card = self._build_kpi_card()
        root.addWidget(self.kpi_card)

        self.charts_widget = QWidget()

        charts_grid = QGridLayout(self.charts_widget)
        charts_grid.setContentsMargins(0, 0, 0, 0)
        charts_grid.setHorizontalSpacing(10)
        charts_grid.setVerticalSpacing(10)

        output_card, self.output_chart_view = self._build_chart_card("Output Over Time")
        buff_card, self.buff_chart_view = self._build_chart_card("Your Buff Uptime")
        debuff_card, self.debuff_chart_view = self._build_chart_card("Debuffs You Applied")
        abilities_card, self.abilities_chart_view = self._build_chart_card("Top Abilities")

        self.output_card = output_card
        self.buff_card = buff_card
        self.debuff_card = debuff_card
        self.abilities_card = abilities_card

        charts_grid.addWidget(output_card, 0, 0, 1, 2)
        charts_grid.addWidget(buff_card, 1, 0)
        charts_grid.addWidget(debuff_card, 1, 1)
        charts_grid.addWidget(abilities_card, 2, 0, 1, 2)

        charts_grid.setColumnStretch(0, 1)
        charts_grid.setColumnStretch(1, 1)

        root.addWidget(self.charts_widget, 1)

        self.empty_state = FoundryEmptyState(
            "Load a fight, pick who you are in it, then Show My Performance."
        )
        root.addWidget(self.empty_state)

        self._set_results_visible(False)

    def _build_source_card(self) -> FoundryCard:

        card = FoundryCard("Report Source")

        self.member_name = QLineEdit()
        self.member_name.setPlaceholderText("Tab label, e.g. your character name")
        self.member_name.textChanged.connect(self.nameChanged.emit)

        self.report_code = QLineEdit()
        self.report_code.setPlaceholderText(
            "Report code, e.g. FPy6Tc9BzwQNbfVK "
            "(from esologs.com/reports/<code>)"
        )

        self.fight_id = QLineEdit()
        self.fight_id.setPlaceholderText("Fight #, e.g. 43")
        self.fight_id.setFixedWidth(80)

        self.load_fight_button = FoundryButton(
            "Load Fight", role=ButtonRole.PRIMARY, compact=True,
        )
        self.load_fight_button.clicked.connect(self.loadFightRequested.emit)

        self.who_am_i = QComboBox()
        self.who_am_i.setEnabled(False)
        self.who_am_i.currentIndexChanged.connect(self._on_actor_selected)

        self.role_override = QComboBox()
        self.role_override.addItems(ROLE_OPTIONS)

        self.show_button = FoundryButton(
            "Show My Performance", role=ButtonRole.SUCCESS, compact=True,
        )
        self.show_button.setEnabled(False)
        self.show_button.clicked.connect(self.showPerformanceRequested.emit)

        self.fight_summary_label = QLabel("No fight loaded yet.")
        self.fight_summary_label.setWordWrap(True)

        form = QFormLayout()

        form.addRow("Member", self.member_name)

        report_row = QHBoxLayout()
        report_row.addWidget(self.report_code, 3)
        report_row.addWidget(QLabel("Fight"))
        report_row.addWidget(self.fight_id, 1)
        report_row.addWidget(self.load_fight_button)

        form.addRow("Report", report_row)

        who_row = QHBoxLayout()
        who_row.addWidget(self.who_am_i, 3)
        who_row.addWidget(QLabel("Role"))
        who_row.addWidget(self.role_override, 1)
        who_row.addWidget(self.show_button)

        form.addRow("Who Am I?", who_row)

        card.addLayout(form)
        card.addWidget(self.fight_summary_label)

        return card

    def _build_kpi_card(self) -> FoundryCard:

        card = FoundryCard("At a Glance")

        row = QHBoxLayout()

        self.kpi_duration = _StatBlock("Fight Length")
        self.kpi_total = _StatBlock("Total Output")
        self.kpi_rate = _StatBlock("Output Rate")
        self.kpi_peak = _StatBlock("Best Stretch")

        for block in (self.kpi_duration, self.kpi_total, self.kpi_rate, self.kpi_peak):
            row.addWidget(block, 1)

        card.addLayout(row)

        return card

    def _build_chart_card(self, title: str) -> tuple[FoundryCard, QChartView]:

        card = FoundryCard(title)

        chart_view = QChartView(_empty_chart("No data yet"))
        chart_view.setMinimumHeight(220)
        chart_view.setStyleSheet(f"background-color: {Colors.SURFACE};")

        card.addWidget(chart_view)

        return card, chart_view

    def _set_results_visible(self, visible: bool):

        self.kpi_card.setVisible(visible)
        self.charts_widget.setVisible(visible)
        self.empty_state.setVisible(not visible)

    # --------------------------------------------------
    # Who Am I? / role picker
    # --------------------------------------------------

    def set_actor_choices(self, choices: list[ActorChoice]):
        """Populate the 'Who Am I?' dropdown after a fight is loaded."""

        self._actor_choices = choices

        self.who_am_i.blockSignals(True)
        self.who_am_i.clear()

        if not choices:
            self.who_am_i.addItem("No players found in this fight")
            self.who_am_i.setEnabled(False)
            self.show_button.setEnabled(False)
        else:
            for choice in choices:
                self.who_am_i.addItem(choice.Label, choice)
            self.who_am_i.setEnabled(True)

        self.who_am_i.blockSignals(False)

        if choices:
            self.who_am_i.setCurrentIndex(0)
            self._on_actor_selected(0)

    def _on_actor_selected(self, index: int):

        choice = self.selected_actor()

        self.show_button.setEnabled(choice is not None)

        if choice is not None and choice.Role in ROLE_OPTIONS:
            self.role_override.setCurrentText(choice.Role)

    def selected_actor(self) -> ActorChoice | None:

        if not self._actor_choices:
            return None

        return self.who_am_i.currentData()

    def selected_role(self) -> str:

        return self.role_override.currentText()

    # --------------------------------------------------
    # Report / fight fields
    # --------------------------------------------------

    @property
    def report_code_value(self) -> str:
        return self.report_code.text().strip()

    @property
    def fight_id_value(self) -> str:
        return self.fight_id.text().strip()

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

    # --------------------------------------------------
    # Results
    # --------------------------------------------------

    def show_snapshot(self, snapshot: PerformanceSnapshot):

        self._last_snapshot = snapshot

        self._set_results_visible(True)

        role_color = Colors.ROLE.get(snapshot.Role.casefold(), Colors.ACCENT)

        self.kpi_duration.set_value(f"{snapshot.FightDurationSeconds:,.0f}s")
        self.kpi_total.set_value(f"{snapshot.OutputTotal:,.0f} {snapshot.OutputLabel}")
        self.kpi_rate.set_value(f"{snapshot.OutputPerSecond:,.0f} {snapshot.OutputRateLabel}")
        self.kpi_peak.set_value(snapshot.PeakWindowLabel)

        self.output_card.title_label.setText(
            f"{snapshot.OutputLabel} Over Time ({snapshot.OutputRateLabel})"
        )
        self._update_output_chart(snapshot.OutputSeries, role_color, snapshot.OutputRateLabel)

        self._update_uptime_chart(self.buff_chart_view, snapshot.BuffUptimes, Colors.ACCENT_LIGHT)
        self._update_uptime_chart(self.debuff_chart_view, snapshot.DebuffUptimes, Colors.WARNING)

        self.abilities_card.title_label.setText(f"Top Abilities by {snapshot.OutputLabel}")
        self._update_abilities_chart(snapshot.TopAbilities, role_color)

    def _update_output_chart(self, points, color: str, rate_label: str):

        if not points:
            self.output_chart_view.setChart(_empty_chart("No output data yet"))
            return

        chart = _new_chart()

        series = QLineSeries()
        series.setColor(QColor(color))

        for t, v in points:
            series.append(t, v)

        chart.addSeries(series)

        axis_x = QValueAxis()
        axis_x.setTitleText("Time (s)")
        axis_x.setLabelFormat("%d")
        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(axis_x)

        axis_y = QValueAxis()
        axis_y.setTitleText(rate_label)
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_y)

        self.output_chart_view.setChart(chart)

    def _update_uptime_chart(self, chart_view: QChartView, uptimes, color: str):

        if not uptimes:
            chart_view.setChart(_empty_chart("No matching effects found"))
            return

        chart = _new_chart()

        bar_set = QBarSet("Uptime %")
        bar_set.setColor(QColor(color))

        categories = []

        # Reversed so the #1 (highest-uptime) entry ends up drawn at
        # the top of the horizontal bar chart, matching reading order.
        for uptime in reversed(uptimes):
            bar_set.append(uptime.UptimePercent)
            categories.append(uptime.Name)

        series = QHorizontalBarSeries()
        series.append(bar_set)
        series.setLabelsVisible(True)

        chart.addSeries(series)

        axis_y = QBarCategoryAxis()
        axis_y.append(categories)
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_y)

        axis_x = QValueAxis()
        axis_x.setRange(0, 100)
        axis_x.setLabelFormat("%d%%")
        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(axis_x)

        chart_view.setChart(chart)

    def _update_abilities_chart(self, abilities, color: str):

        if not abilities:
            self.abilities_chart_view.setChart(_empty_chart("No ability data yet"))
            return

        chart = _new_chart()

        bar_set = QBarSet("Total")
        bar_set.setColor(QColor(color))

        categories = []

        for ability in abilities:
            bar_set.append(ability.Total)
            categories.append(ability.Name)

        series = QBarSeries()
        series.append(bar_set)

        chart.addSeries(series)

        axis_x = QBarCategoryAxis()
        axis_x.append(categories)
        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(axis_x)

        axis_y = QValueAxis()
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_y)

        self.abilities_chart_view.setChart(chart)

    # --------------------------------------------------
    # Model (persistence -- pick only, not the computed snapshot)
    # --------------------------------------------------

    @property
    def model(self) -> PerformanceProfile:

        choice = self.selected_actor()

        actor_id = choice.ActorId if choice else self._last_profile.ActorId
        actor_label = choice.Label if choice else self._last_profile.ActorLabel
        role = self.selected_role() if choice else self._last_profile.Role

        return PerformanceProfile(
            Name=self.member_name.text().strip(),
            ReportCode=self.report_code_value,
            FightId=self.fight_id_value,
            ActorId=actor_id,
            ActorLabel=actor_label,
            Role=role or "DPS",
        )

    def load(self, profile: PerformanceProfile):

        self._last_profile = profile

        self.member_name.setText(profile.Name)
        self.report_code.setText(profile.ReportCode)
        self.fight_id.setText(profile.FightId)

        if profile.Role in ROLE_OPTIONS:
            self.role_override.setCurrentText(profile.Role)

        self._set_results_visible(False)

        if profile.ActorLabel:
            self.fight_summary_label.setText(
                f"Last time this was {profile.ActorLabel} ({profile.Role}) -- "
                "Load Fight again to pick and re-fetch."
            )
        else:
            self.fight_summary_label.setText("No fight loaded yet.")

    def clear(self):

        self._last_profile = PerformanceProfile()
        self._last_snapshot = None

        self.load(PerformanceProfile())

        self.who_am_i.clear()
        self.who_am_i.setEnabled(False)
        self._actor_choices = []
