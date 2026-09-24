from __future__ import annotations

"""Fancy Review workspace for cross-pull Major Brittle uptime."""

from pathlib import Path

from PySide6.QtCore import Qt, QMargins
from PySide6.QtGui import QColor, QPainter
from PySide6.QtCharts import (
    QBarCategoryAxis,
    QBarSeries,
    QBarSet,
    QChart,
    QChartView,
    QHorizontalBarSeries,
    QValueAxis,
)
from PySide6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QApplication,
)

from services.accessibility_preferences import VISUAL_THEME_RYLO
from services.brittle_uptime_service import BrittleUptimeService
from services.esologs_client import EsoLogsApiError, EsoLogsClient
from services.settings_service import SettingsService
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar
from ui.foundry_page import FoundryPage
from ui.theme.colors import Colors
from ui.theme.fonts import Fonts


def _duration(seconds: float) -> str:
    total = max(0, int(round(float(seconds or 0.0))))
    minutes, second = divmod(total, 60)
    hours, minute = divmod(minutes, 60)
    if hours:
        return f"{hours:d}:{minute:02d}:{second:02d}"
    return f"{minute:02d}:{second:02d}"


def _is_rylo() -> bool:
    app = QApplication.instance()
    return bool(app is not None and app.property("visualTheme") == VISUAL_THEME_RYLO)


def _chart_palette() -> dict[str, str]:
    if _is_rylo():
        return {
            "surface": "#111519",
            "gold": "#8C8580",
            "accent": "#8B0E14",
            "text": "#D8D0C2",
            "muted": "#99928A",
            "border": "#45484C",
        }
    return {
        "surface": Colors.SURFACE,
        "gold": Colors.GOLD,
        "accent": Colors.ACCENT_LIGHT,
        "text": Colors.TEXT,
        "muted": Colors.TEXT_MUTED,
        "border": Colors.BORDER,
    }


def _new_chart(title: str = "") -> QChart:
    colors = _chart_palette()
    chart = QChart()
    chart.setBackgroundBrush(QColor(colors["surface"]))
    chart.setBackgroundRoundness(0)
    chart.setMargins(QMargins(8, 8, 8, 8))
    chart.legend().hide()
    chart.setTitle(title)
    chart.setTitleBrush(QColor(colors["gold"]))
    return chart


def _style_axis(axis, *, grid: bool = True) -> None:
    colors = _chart_palette()
    axis.setLabelsColor(QColor(colors["text"]))
    axis.setLinePen(QColor(colors["border"]))
    if grid:
        axis.setGridLineColor(QColor(colors["border"]))
    else:
        axis.setGridLineVisible(False)


class _MetricTile(QWidget):
    def __init__(self, caption: str, parent=None) -> None:
        super().__init__(parent)
        self.setProperty("brittleMetricTile", True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 9, 12, 9)
        layout.setSpacing(2)

        self.value = QLabel("—")
        self.value.setFont(Fonts.statistic())
        self.value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.value.setStyleSheet(f"color: {_chart_palette()['gold']};")
        layout.addWidget(self.value)

        label = QLabel(caption.upper())
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(f"color: {_chart_palette()['muted']}; font-size: 10px;")
        layout.addWidget(label)

    def set_value(self, text: str) -> None:
        self.value.setText(text)


class BrittleUptimePage(FoundryPage):
    """Read-only Major Brittle comparison desk backed by the ESO Logs API."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.settings_service = SettingsService(Path("settings.json"))
        self._report = None
        self._build_ui()
        self._load_default_actor()

    def _build_client(self) -> EsoLogsClient:
        settings = self.settings_service.load()
        return EsoLogsClient(
            client_id=settings.get("EsoLogsClientId", ""),
            client_secret=settings.get("EsoLogsClientSecret", ""),
        )

    def _build_ui(self) -> None:
        self.header = FoundryHeader(
            title="Brittle Uptime",
            subtitle="Pull-by-pull Major Brittle uptime for a selected ESO Logs actor, with raid-wide context.",
            department="RAID • REVIEW",
            icon="archive",
        )
        self.set_header(self.header)

        hero = FoundryCard("Selected Actor · Major Brittle", "compass")
        hero_grid = QGridLayout()
        hero_grid.setHorizontalSpacing(12)
        hero_grid.setVerticalSpacing(7)

        title = QLabel("MAJOR BRITTLE UPTIME")
        title.setFont(Fonts.section_title())
        title.setStyleSheet(f"color: {_chart_palette()['gold']};")
        hero_grid.addWidget(title, 0, 0, 1, 4)

        subtitle = QLabel(
            "Primary measurement: Major Brittle applied by the selected ESO Logs actor. "
            "Raid-wide uptime is shown only as encounter context."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"color: {_chart_palette()['muted']};")
        hero_grid.addWidget(subtitle, 1, 0, 1, 4)

        self.report_input = QLineEdit()
        self.report_input.setPlaceholderText("ESO Logs report URL or code")
        self.report_input.returnPressed.connect(self.load_report)
        hero_grid.addWidget(self.report_input, 2, 0, 1, 2)

        self.fights_input = QLineEdit()
        self.fights_input.setPlaceholderText("Fight IDs, e.g. 6,21,25,32")
        self.fights_input.returnPressed.connect(self.load_report)
        hero_grid.addWidget(self.fights_input, 2, 2)

        self.actor_input = QLineEdit()
        self.actor_input.setPlaceholderText("Actor ID, e.g. 72")
        self.actor_input.setToolTip("ESO Logs source actor ID for the Major Brittle provider in this report.")
        self.actor_input.returnPressed.connect(self.load_report)
        hero_grid.addWidget(self.actor_input, 3, 0)

        self.save_actor_button = QPushButton("Save Default Actor")
        self.save_actor_button.clicked.connect(self._save_default_actor)
        hero_grid.addWidget(self.save_actor_button, 3, 1)

        controls = QHBoxLayout()
        self.kills_only = QCheckBox("Kills only")
        self.kills_only.setChecked(True)
        controls.addWidget(self.kills_only)

        self.load_button = QPushButton("Analyze Major Brittle")
        self.load_button.setProperty("primary", True)
        self.load_button.clicked.connect(self.load_report)
        controls.addWidget(self.load_button)
        hero_grid.addLayout(controls, 2, 3)

        self.actor_note = QLabel("Actor ID can change from report to report.")
        self.actor_note.setProperty("muted", True)
        hero_grid.addWidget(self.actor_note, 3, 2, 1, 2)

        hero.addLayout(hero_grid)
        self.workspace_layout.addWidget(hero)

        metrics_card = FoundryCard("At a Glance", "chart")
        metrics = QHBoxLayout()
        metrics.setSpacing(8)
        self.count_tile = _MetricTile("Fights")
        self.average_tile = _MetricTile("Average")
        self.best_tile = _MetricTile("Best Pull")
        self.low_tile = _MetricTile("Lowest Pull")
        self.spread_tile = _MetricTile("Spread")
        for tile in (
            self.count_tile,
            self.average_tile,
            self.best_tile,
            self.low_tile,
            self.spread_tile,
        ):
            metrics.addWidget(tile, 1)
        metrics_card.addLayout(metrics)
        self.workspace_layout.addWidget(metrics_card)

        visual_row = QHBoxLayout()
        visual_row.setSpacing(10)

        pull_card = FoundryCard("Uptime by Pull", "chart")
        self.pull_chart_view = QChartView(_new_chart("Load a report to compare pulls"))
        self.pull_chart_view.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.pull_chart_view.setMinimumHeight(300)
        self.pull_chart_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        pull_card.addWidget(self.pull_chart_view)
        visual_row.addWidget(pull_card, 3)

        brief_card = FoundryCard("Evidence Brief", "clipboard")
        self.brief_heading = QLabel("No report loaded")
        self.brief_heading.setFont(Fonts.section_title())
        self.brief_heading.setWordWrap(True)
        brief_card.addWidget(self.brief_heading)

        self.brief_body = QLabel(
            "Load an ESO Logs report and FoundryDock will summarize the strongest pull, "
            "the weakest pull, consistency spread, and provider evidence without inventing a target threshold."
        )
        self.brief_body.setWordWrap(True)
        self.brief_body.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.brief_body.setStyleSheet(f"color: {_chart_palette()['text']};")
        brief_card.addWidget(self.brief_body)

        self.copy_brief_button = QPushButton("Copy Evidence Brief")
        self.copy_brief_button.clicked.connect(self._copy_evidence_brief)
        brief_card.addWidget(self.copy_brief_button)

        proof_note = QLabel(
            "FIELD NOTE\nDuplicate Major Brittle IDs are de-duplicated by effect name. "
            "Provider rows may overlap, so they are not summed into raid uptime."
        )
        proof_note.setWordWrap(True)
        proof_note.setProperty("muted", True)
        proof_note.setStyleSheet(
            f"color: {_chart_palette()['muted']}; border-top: 1px solid {_chart_palette()['border']}; padding-top: 8px;"
        )
        brief_card.addWidget(proof_note)
        visual_row.addWidget(brief_card, 2)

        self.workspace_layout.addLayout(visual_row)

        comparison = FoundryCard("Pull Ledger", "archive")
        self.fight_table = QTableWidget(0, 8)
        self.fight_table.setHorizontalHeaderLabels(
            ["FIGHT", "ENCOUNTER", "RESULT", "DURATION", "ACTOR TIME", "ACTOR UPTIME", "RAID UPTIME", "SOURCE"]
        )
        self.fight_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.fight_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.fight_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.fight_table.verticalHeader().setVisible(False)
        self.fight_table.itemSelectionChanged.connect(self._show_selected_providers)
        self.fight_table.horizontalHeader().setStretchLastSection(True)
        comparison.addWidget(self.fight_table)
        self.workspace_layout.addWidget(comparison)

        detail_row = QHBoxLayout()
        detail_row.setSpacing(10)

        provider_card = FoundryCard("Selected Pull · Actor", "chart")
        self.provider_heading = QLabel("Select a pull")
        self.provider_heading.setFont(Fonts.section_title())
        self.provider_heading.setWordWrap(True)
        provider_card.addWidget(self.provider_heading)

        self.provider_chart_view = QChartView(_new_chart("Provider evidence appears here"))
        self.provider_chart_view.setMinimumHeight(260)
        self.provider_chart_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        provider_card.addWidget(self.provider_chart_view)
        detail_row.addWidget(provider_card, 3)

        provider_table_card = FoundryCard("Actor Ledger", "clipboard")
        self.provider_table = QTableWidget(0, 5)
        self.provider_table.setHorizontalHeaderLabels(
            ["PLAYER", "ROLE", "MAJOR BRITTLE TIME", "SOURCE UPTIME", "ACTOR ID"]
        )
        self.provider_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.provider_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.provider_table.verticalHeader().setVisible(False)
        self.provider_table.horizontalHeader().setStretchLastSection(True)
        provider_table_card.addWidget(self.provider_table)

        provider_note = QLabel(
            "Selected actor source uptime is the monitored number. "
            "Raid-wide Major Brittle is retained only as context for the selected pull."
        )
        provider_note.setWordWrap(True)
        provider_note.setProperty("muted", True)
        provider_table_card.addWidget(provider_note)
        detail_row.addWidget(provider_table_card, 2)

        self.workspace_layout.addLayout(detail_row)

        self.status_bar = FoundryStatusBar()
        self.set_status(self.status_bar)


    def _load_default_actor(self) -> None:
        try:
            settings = self.settings_service.load()
            actor_id = str(settings.get("BrittleDefaultActorId", "72") or "72").strip()
        except Exception:
            actor_id = "72"
        if not actor_id.isdigit() or int(actor_id) <= 0:
            actor_id = "72"
        self.actor_input.setText(actor_id)
        self.actor_note.setText(f"Saved default actor: {actor_id}. Override it here for any report.")

    def _save_default_actor(self) -> None:
        actor_text = self.actor_input.text().strip()
        if not actor_text.isdigit() or int(actor_text) <= 0:
            self.status_bar.warning("Enter a valid positive ESO Logs actor ID before saving it.")
            return
        try:
            settings = self.settings_service.load()
            settings["BrittleDefaultActorId"] = actor_text
            self.settings_service.save(settings)
        except Exception as exc:
            self.status_bar.error(f"Could not save default Brittle actor: {exc}")
            return
        self.actor_note.setText(
            f"Saved default actor: {actor_text}. Override it here for any report."
        )
        self.status_bar.success(f"Saved Major Brittle default actor {actor_text}.")

    def _fight_ids(self) -> tuple[int, ...]:
        text = self.fights_input.text().strip()
        if not text:
            return ()
        values: list[int] = []
        for piece in text.replace(";", ",").split(","):
            cleaned = piece.strip()
            if not cleaned:
                continue
            if not cleaned.isdigit():
                raise ValueError(f"Invalid fight ID: {cleaned}")
            values.append(int(cleaned))
        return tuple(values)

    def load_report(self) -> None:
        report_code = self.report_input.text().strip()
        if not report_code:
            self.status_bar.warning("Enter an ESO Logs report URL or report code.")
            return
        actor_text = self.actor_input.text().strip()
        if not actor_text.isdigit() or int(actor_text) <= 0:
            self.status_bar.warning("Enter a valid positive ESO Logs actor ID.")
            return
        actor_id = int(actor_text)

        self.load_button.setEnabled(False)
        self.status_bar.info("Loading Major Brittle evidence from ESO Logs…")
        try:
            service = BrittleUptimeService(self._build_client())
            self._report = service.analyze(
                report_code,
                fight_ids=self._fight_ids(),
                kills_only=self.kills_only.isChecked(),
                provider_actor_id=actor_id,
            )
            self._render_report()
            self.status_bar.success(
                f"Loaded {len(self._report.fights)} fight(s) from {self._report.report_code}."
            )
        except (EsoLogsApiError, ValueError) as exc:
            self._report = None
            self._clear()
            self.status_bar.error(str(exc))
        except Exception as exc:
            self._report = None
            self._clear()
            self.status_bar.error(f"Brittle analysis failed: {exc}")
        finally:
            self.load_button.setEnabled(True)

    def _clear(self) -> None:
        self.fight_table.setRowCount(0)
        self.provider_table.setRowCount(0)
        self.provider_heading.setText("Select a pull")
        for tile in (
            self.count_tile,
            self.average_tile,
            self.best_tile,
            self.low_tile,
            self.spread_tile,
        ):
            tile.set_value("—")
        self.brief_heading.setText("No report loaded")
        self.brief_body.setText("Load a report to build the Brittle evidence brief.")
        self.pull_chart_view.setChart(_new_chart("No pull data"))
        self.provider_chart_view.setChart(_new_chart("No provider data"))

    def _render_report(self) -> None:
        report = self._report
        if report is None:
            self._clear()
            return

        spread = max(0.0, report.best_percent - report.lowest_percent)
        self.count_tile.set_value(str(len(report.fights)))
        self.average_tile.set_value(f"{report.average_percent:.1f}%")
        self.best_tile.set_value(f"{report.best_percent:.1f}%")
        self.low_tile.set_value(f"{report.lowest_percent:.1f}%")
        self.spread_tile.set_value(f"{spread:.1f} pts")

        self._render_pull_chart()
        self._render_brief()

        self.fight_table.setRowCount(len(report.fights))
        for row_index, fight in enumerate(report.fights):
            top_source = fight.providers[0].actor_label if fight.providers else "—"
            values = (
                str(fight.fight_id),
                fight.fight_name,
                "KILL" if fight.kill else "WIPE",
                _duration(fight.duration_seconds),
                f"{fight.brittle_seconds:.1f}s",
                f"{fight.brittle_percent:.1f}%",
                f"{fight.raid_brittle_percent:.1f}%",
                top_source,
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, row_index)
                if column in (0, 2, 4, 5, 6):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.fight_table.setItem(row_index, column, item)

        self.fight_table.resizeColumnsToContents()
        self.fight_table.resizeRowsToContents()
        if report.fights:
            self.fight_table.selectRow(0)
        else:
            self.provider_table.setRowCount(0)
            self.provider_heading.setText("No matching fights")
            self.provider_chart_view.setChart(_new_chart("No provider data"))

    def _render_pull_chart(self) -> None:
        report = self._report
        chart = _new_chart("Major Brittle · Selected Actor Uptime")
        if report is None or not report.fights:
            chart.setTitle("No matching fights")
            self.pull_chart_view.setChart(chart)
            return

        values = QBarSet("Major Brittle")
        values.setColor(QColor(_chart_palette()["gold"]))
        categories: list[str] = []
        for fight in report.fights:
            values.append(float(fight.brittle_percent))
            categories.append(f"#{fight.fight_id}")

        series = QBarSeries()
        series.append(values)
        chart.addSeries(series)

        axis_x = QBarCategoryAxis()
        axis_x.append(categories)
        _style_axis(axis_x, grid=False)
        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(axis_x)

        axis_y = QValueAxis()
        axis_y.setRange(0.0, 100.0)
        axis_y.setTickCount(6)
        axis_y.setLabelFormat("%.0f%%")
        _style_axis(axis_y)
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_y)

        self.pull_chart_view.setChart(chart)

    def _render_provider_chart(self, fight) -> None:
        chart = _new_chart("Source-attributed Major Brittle uptime")
        if not fight.providers:
            chart.setTitle("No source-attributed Major Brittle provider found")
            self.provider_chart_view.setChart(chart)
            return

        series = QHorizontalBarSeries()
        values = QBarSet("Source uptime")
        values.setColor(QColor(_chart_palette()["accent"]))
        categories: list[str] = []
        for provider in reversed(fight.providers[:8]):
            values.append(float(provider.uptime_percent))
            categories.append(provider.actor_label)
        series.append(values)
        chart.addSeries(series)

        axis_y = QBarCategoryAxis()
        axis_y.append(categories)
        _style_axis(axis_y, grid=False)
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_y)

        axis_x = QValueAxis()
        axis_x.setRange(0.0, 100.0)
        axis_x.setTickCount(6)
        axis_x.setLabelFormat("%.0f%%")
        _style_axis(axis_x)
        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(axis_x)

        self.provider_chart_view.setChart(chart)

    def _render_brief(self) -> None:
        report = self._report
        if report is None or not report.fights:
            self.brief_heading.setText("No matching fights")
            self.brief_body.setText("Nothing to summarize.")
            return

        best = max(report.fights, key=lambda row: row.brittle_percent)
        low = min(report.fights, key=lambda row: row.brittle_percent)
        spread = best.brittle_percent - low.brittle_percent

        provider_totals: dict[str, float] = {}
        for fight in report.fights:
            for provider in fight.providers:
                provider_totals[provider.actor_label] = (
                    provider_totals.get(provider.actor_label, 0.0) + provider.uptime_seconds
                )
        top_provider = (
            max(provider_totals.items(), key=lambda row: row[1])[0]
            if provider_totals
            else "No source-attributed provider"
        )

        self.brief_heading.setText(f"{len(report.fights)} pull evidence set")
        self.brief_body.setText(
            f"{top_provider} Major Brittle averaged {report.average_percent:.1f}% across the selected fights.\n\n"
            f"Strongest observed pull: Fight {best.fight_id} at {best.brittle_percent:.1f}%.\n"
            f"Lowest observed pull: Fight {low.fight_id} at {low.brittle_percent:.1f}%.\n"
            f"Observed spread: {spread:.1f} percentage points.\n\n"
            f"Most source-attributed Brittle time across these pulls: {top_provider}.\n\n"
            "No performance target is assumed here. This page reports observed log evidence only."
        )

    def _copy_evidence_brief(self) -> None:
        report = self._report
        if report is None or not report.fights:
            self.status_bar.warning("Load Brittle evidence before copying a brief.")
            return

        lines = [
            f"Major Brittle uptime · ESO Logs {report.report_code}",
            f"Selected fights: {', '.join(str(row.fight_id) for row in report.fights)}",
            f"Average selected-actor uptime: {report.average_percent:.1f}%",
            f"Best observed: {report.best_percent:.1f}%",
            f"Lowest observed: {report.lowest_percent:.1f}%",
            "",
            "Pulls:",
        ]
        for fight in report.fights:
            provider = fight.providers[0].actor_label if fight.providers else "no source-attributed provider"
            lines.append(
                f"Fight {fight.fight_id}: {fight.brittle_percent:.1f}% "
                f"({fight.brittle_seconds:.1f}s / {fight.duration_seconds:.1f}s), "
                f"top source {provider}"
            )
        lines.extend(
            [
                "",
                "Note: headline uptime is source-attributed Major Brittle from the selected actor.",
                "Raid-wide Major Brittle is shown only as pull context.",
                "Duplicate named Major Brittle aura IDs are de-duplicated rather than added together.",
            ]
        )
        QApplication.clipboard().setText("\n".join(lines))
        self.status_bar.success("Copied the Brittle evidence brief to the clipboard.")

    def _show_selected_providers(self) -> None:
        if self._report is None:
            return
        selected = self.fight_table.selectionModel().selectedRows()
        if not selected:
            return
        row_index = selected[0].row()
        if row_index < 0 or row_index >= len(self._report.fights):
            return

        fight = self._report.fights[row_index]
        self.provider_heading.setText(
            f"Fight {fight.fight_id} · {fight.fight_name} · raid uptime {fight.brittle_percent:.1f}%"
        )
        self._render_provider_chart(fight)

        self.provider_table.setRowCount(len(fight.providers))
        for row, provider in enumerate(fight.providers):
            values = (
                provider.actor_label,
                provider.role,
                f"{provider.uptime_seconds:.1f}s",
                f"{provider.uptime_percent:.1f}%",
                str(provider.actor_id),
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column in (2, 3, 4):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.provider_table.setItem(row, column, item)
        self.provider_table.resizeColumnsToContents()
        self.provider_table.resizeRowsToContents()


__all__ = ["BrittleUptimePage"]
