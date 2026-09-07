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

import requests

from PySide6.QtCore import Qt, Signal, QMargins
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtCharts import (
    QBarCategoryAxis,
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
    QProgressBar,
    QSizePolicy,
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


def _style_axis(axis, grid: bool = True):
    """
    QtCharts axes default to unstyled (effectively black-on-
    near-black) label text, which is invisible on this app's dark
    theme -- every axis this file creates must go through here or
    its labels silently disappear, exactly what happened to the
    category (ability-name) labels on the uptime bar charts.
    """

    axis.setLabelsColor(QColor(Colors.TEXT))
    axis.setLinePen(QColor(Colors.BORDER))

    if grid:
        axis.setGridLineColor(QColor(Colors.BORDER))
    else:
        axis.setGridLineVisible(False)

    return axis


def _empty_chart(message: str) -> QChart:

    chart = _new_chart()
    chart.setTitle(message)

    return chart


# ESO Logs (RPGLogs family) serves static assets from
# assets.rpglogs.com -- confirmed via RPGLogs' own docs/GitHub org.
# This exact per-game ability-icon subpath is NOT independently
# confirmed against a live URL, though; if icons never appear, this
# template is the first thing to check against a real icon URL
# copied from an esologs.com report page.
ABILITY_ICON_URL_TEMPLATE = "https://assets.rpglogs.com/img/eso/abilities/{icon}.png"

_ICON_SIZE = 20

_icon_cache: dict[str, QPixmap | None] = {}


def _fetch_ability_icon(icon_slug: str) -> QPixmap | None:
    """
    Best-effort ability icon fetch, cached per slug for the process
    lifetime. Any failure (network, 404, bad image bytes, wrong URL
    template) just returns None -- callers fall back to a plain
    colored square, never a broken-image glyph or a crash.
    """

    if not icon_slug:
        return None

    if icon_slug in _icon_cache:
        return _icon_cache[icon_slug]

    pixmap = None

    try:
        response = requests.get(
            ABILITY_ICON_URL_TEMPLATE.format(icon=icon_slug), timeout=3,
        )
        if response.status_code == 200 and response.content:
            candidate = QPixmap()
            if candidate.loadFromData(response.content):
                pixmap = candidate
    except Exception:
        pixmap = None

    _icon_cache[icon_slug] = pixmap

    return pixmap


class _AbilityRow(QWidget):
    """One row in the Top Abilities list: icon, name, a proportional
    mini-bar, and the raw value -- compact enough that several fit
    in half the width a full bar chart with text-label bars needed."""

    def __init__(
        self,
        name: str,
        icon_slug: str,
        value_text: str,
        percent: float,
        color: str,
        parent=None,
    ):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 1, 0, 1)
        layout.setSpacing(6)

        icon_label = QLabel()
        icon_label.setFixedSize(_ICON_SIZE, _ICON_SIZE)

        pixmap = _fetch_ability_icon(icon_slug)

        if pixmap is not None:
            icon_label.setPixmap(
                pixmap.scaled(
                    _ICON_SIZE, _ICON_SIZE,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        else:
            icon_label.setStyleSheet(
                f"background-color: {Colors.SURFACE_LIGHT}; border-radius: 3px;"
            )

        name_label = QLabel()
        name_label.setStyleSheet(f"color: {Colors.TEXT}; font-size: 11px;")
        name_label.setFixedWidth(84)
        name_label.setToolTip(name)
        metrics = name_label.fontMetrics()
        name_label.setText(metrics.elidedText(name, Qt.TextElideMode.ElideRight, 84))

        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(int(max(0.0, min(100.0, percent))))
        bar.setTextVisible(False)
        bar.setFixedHeight(8)
        bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        bar.setStyleSheet(
            f"QProgressBar {{ background-color: {Colors.SURFACE_LIGHT}; "
            f"border: none; border-radius: 4px; }}"
            f"QProgressBar::chunk {{ background-color: {color}; border-radius: 4px; }}"
        )

        value_label = QLabel(value_text)
        value_label.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 10px;")
        value_label.setFixedWidth(52)
        value_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        layout.addWidget(icon_label)
        layout.addWidget(name_label)
        layout.addWidget(bar, 1)
        layout.addWidget(value_label)


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

        output_card, self.output_chart_view = self._build_chart_card(
            "Output Over Time"
        )
        buff_card, self.buff_chart_view = self._build_chart_card(
            "Your Buff Uptime", compact=True
        )
        debuff_card, self.debuff_chart_view = self._build_chart_card(
            "Debuffs You Applied", compact=True
        )
        raid_debuff_card, self.raid_debuff_chart_view = self._build_chart_card(
            "Boss Debuffs (Raid-Wide)", compact=True
        )
        abilities_card, self.abilities_list_layout = self._build_ability_list_card(
            "Top Abilities"
        )

        self.output_card = output_card
        self.buff_card = buff_card
        self.debuff_card = debuff_card
        self.raid_debuff_card = raid_debuff_card
        self.abilities_card = abilities_card

        # Row 0: the one detailed time-series chart, full width.
        # Row 1: Your Buff Uptime | Debuffs You Applied, 50/50.
        # Row 2: Boss Debuffs (Raid-Wide) | Top Abilities, but Top
        # Abilities is a compact icon list (no long text-label bars
        # to fit), so it only needs half that width -- wrapped in
        # its own row so this doesn't skew row 1's 50/50 split.
        charts_grid.addWidget(output_card, 0, 0, 1, 2)
        charts_grid.addWidget(buff_card, 1, 0)
        charts_grid.addWidget(debuff_card, 1, 1)

        row2 = QWidget()
        row2_layout = QHBoxLayout(row2)
        row2_layout.setContentsMargins(0, 0, 0, 0)
        row2_layout.setSpacing(10)
        row2_layout.addWidget(raid_debuff_card, 2)
        row2_layout.addWidget(abilities_card, 1)

        charts_grid.addWidget(row2, 2, 0, 1, 2)

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

        self.immunity_buff_name = QLineEdit()
        self.immunity_buff_name.setPlaceholderText(
            "Optional -- name of the boss's immunity buff/debuff "
            "(used to compute boss-active time for uptime %)"
        )

        self.immunity_buff_kind = QComboBox()
        self.immunity_buff_kind.addItems(["Buff", "Debuff"])
        self.immunity_buff_kind.setToolTip(
            "Whether the boss's immunity shows up as a buff the boss "
            "gains, or a debuff that has to fall off the boss to end "
            "the immunity window."
        )

        immunity_row = QHBoxLayout()
        immunity_row.addWidget(self.immunity_buff_name, 3)
        immunity_row.addWidget(self.immunity_buff_kind, 1)

        form.addRow("Boss Immunity Buff", immunity_row)

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

    def _build_chart_card(self, title: str, compact: bool = False) -> tuple[FoundryCard, QChartView]:
        """
        compact=True is for bar-chart cards (buff/debuff/raid-debuff/
        top-abilities) which just show name + a single percentage or
        total per row -- they don't need the height a detailed
        time-series line chart does, so keep them short and let more
        of them fit on screen at once.
        """

        card = FoundryCard(title)

        chart_view = QChartView(_empty_chart("No data yet"))
        chart_view.setMinimumHeight(130 if compact else 220)
        chart_view.setMaximumHeight(160 if compact else 16777215)
        chart_view.setStyleSheet(f"background-color: {Colors.SURFACE};")

        card.addWidget(chart_view)
        card.set_body_margins(8, 4, 8, 4)

        return card, chart_view

    def _build_ability_list_card(self, title: str) -> tuple[FoundryCard, QVBoxLayout]:
        """Compact icon+bar list, used for Top Abilities instead of a
        QChart bar chart -- no long text-label bars means it fits in
        roughly half the width."""

        card = FoundryCard(title)
        card.set_body_margins(8, 4, 8, 4)
        card.set_body_spacing(3)

        list_widget = QWidget()
        list_layout = QVBoxLayout(list_widget)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(3)

        placeholder = QLabel("No data yet")
        placeholder.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 11px;")
        list_layout.addWidget(placeholder)

        card.addWidget(list_widget)

        return card, list_layout

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

    @property
    def immunity_buff_name_value(self) -> str:
        return self.immunity_buff_name.text().strip()

    @property
    def immunity_buff_kind_value(self) -> str:
        return self.immunity_buff_kind.currentText()

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

        if snapshot.BossActiveSeconds is not None:
            self.kpi_duration.set_value(
                f"{snapshot.FightDurationSeconds:,.0f}s "
                f"({snapshot.BossActiveSeconds:,.0f}s active)"
            )
        else:
            self.kpi_duration.set_value(f"{snapshot.FightDurationSeconds:,.0f}s")

        self.kpi_total.set_value(f"{snapshot.OutputTotal:,.0f} {snapshot.OutputLabel}")
        self.kpi_rate.set_value(f"{snapshot.OutputPerSecond:,.0f} {snapshot.OutputRateLabel}")
        self.kpi_peak.set_value(snapshot.PeakWindowLabel)

        self.output_card.title_label.setText(
            f"{snapshot.OutputLabel} Over Time ({snapshot.OutputRateLabel})"
        )
        self._update_output_chart(snapshot.OutputSeries, role_color, snapshot.OutputRateLabel)

        uptime_basis = "vs boss-active" if snapshot.BossActiveSeconds is not None else "vs full fight"

        self.buff_card.title_label.setText(f"Your Buff Uptime ({uptime_basis})")
        self.debuff_card.title_label.setText(f"Debuffs You Applied ({uptime_basis})")
        self.raid_debuff_card.title_label.setText(f"Boss Debuffs, Raid-Wide ({uptime_basis})")

        self._update_uptime_chart(self.buff_chart_view, snapshot.BuffUptimes, Colors.ACCENT_LIGHT)
        self._update_uptime_chart(self.debuff_chart_view, snapshot.DebuffUptimes, Colors.WARNING)
        self._update_uptime_chart(self.raid_debuff_chart_view, snapshot.RaidDebuffUptimes, Colors.GOLD)

        self.abilities_card.title_label.setText(f"Top Abilities by {snapshot.OutputLabel}")
        self._update_abilities_list(snapshot.TopAbilities, role_color)

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
        _style_axis(axis_x)
        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(axis_x)

        axis_y = QValueAxis()
        axis_y.setTitleText(rate_label)
        _style_axis(axis_y)
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
        _style_axis(axis_y, grid=False)
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_y)

        axis_x = QValueAxis()
        axis_x.setRange(0, 100)
        axis_x.setLabelFormat("%d%%")
        _style_axis(axis_x)
        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(axis_x)

        chart_view.setChart(chart)

    def _update_abilities_list(self, abilities, color: str):

        layout = self.abilities_list_layout

        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not abilities:
            placeholder = QLabel("No ability data yet")
            placeholder.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 11px;")
            layout.addWidget(placeholder)
            return

        max_total = max((a.Total for a in abilities), default=0.0) or 1.0

        for ability in abilities:

            percent = (ability.Total / max_total) * 100.0

            layout.addWidget(
                _AbilityRow(
                    name=ability.Name,
                    icon_slug=ability.IconSlug,
                    value_text=f"{ability.Total:,.0f}",
                    percent=percent,
                    color=color,
                )
            )

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
            ImmunityBuffName=self.immunity_buff_name_value,
            ImmunityBuffKind=self.immunity_buff_kind_value,
        )

    def load(self, profile: PerformanceProfile):

        self._last_profile = profile

        self.member_name.setText(profile.Name)
        self.report_code.setText(profile.ReportCode)
        self.fight_id.setText(profile.FightId)
        self.immunity_buff_name.setText(profile.ImmunityBuffName)
        self.immunity_buff_kind.setCurrentText(profile.ImmunityBuffKind or "Buff")

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
