from __future__ import annotations

"""Boss-active graph shading and dashboard row-balance cleanup.

When an exact immunity aura marker is configured, the Performance Dashboard can
now paint the periods where the boss is damageable as quiet background bands
behind the healing/damage line.  Aggregate active seconds remain valid when
exact events are unavailable, but no bands are fabricated from a percentage.

This layer also keeps the left-hand cards from vertically stretching when the
support-effect list on the right grows taller.
"""

from PySide6.QtCore import Qt
from PySide6.QtCharts import QAreaSeries, QLineSeries, QValueAxis
from PySide6.QtGui import QColor, QPen
from PySide6.QtWidgets import QSizePolicy

from ui.components.foundry_card import FoundryCard
from ui.theme.colors import Colors

_INSTALLED = False


def _balance_cards(page) -> None:
    """Keep paired cards content-height instead of stretching to their neighbor."""
    for card in page.findChildren(FoundryCard):
        title = card.title_label.text().strip()
        if title in {
            "Report Source",
            "Track Specific Buffs / Debuffs",
            "At a Glance",
            "Support Effect Uptime",
        }:
            card.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Preferred,
            )
            card.setMaximumHeight(card.sizeHint().height())


def _extract_snapshot_args(args, kwargs):
    names = ("report_code", "fight_id", "actor_id")
    values = {}
    for index, name in enumerate(names):
        if name in kwargs:
            values[name] = kwargs[name]
        elif index < len(args):
            values[name] = args[index]
        else:
            values[name] = None

    if "immunity_buff_name" in kwargs:
        immunity_name = kwargs["immunity_buff_name"]
    elif len(args) > 5:
        immunity_name = args[5]
    else:
        immunity_name = ""

    if "immunity_buff_kind" in kwargs:
        immunity_kind = kwargs["immunity_buff_kind"]
    elif len(args) > 6:
        immunity_kind = args[6]
    else:
        immunity_kind = "Buff"

    return (
        values["report_code"],
        values["fight_id"],
        values["actor_id"],
        immunity_name,
        immunity_kind,
    )


def _shade_active_windows(page, points) -> None:
    snapshot = getattr(page, "_last_snapshot", None)
    if snapshot is None:
        return

    active_windows = list(getattr(snapshot, "BossActiveWindows", ()) or ())
    if not active_windows or not points:
        if hasattr(page, "output_card"):
            page.output_card.set_badge("")
        return

    chart = page.output_chart_view.chart()
    if chart is None:
        return

    axes_x = [axis for axis in chart.axes(Qt.Orientation.Horizontal) if isinstance(axis, QValueAxis)]
    axes_y = [axis for axis in chart.axes(Qt.Orientation.Vertical) if isinstance(axis, QValueAxis)]
    if not axes_x or not axes_y:
        return
    axis_x = axes_x[0]
    axis_y = axes_y[0]

    # The output line is created by the canonical dashboard.  Move it to the end
    # of the series stack after adding bands so it is always painted on top.
    output_series = next((series for series in chart.series() if isinstance(series, QLineSeries)), None)
    if output_series is None:
        return

    y_min = min(0.0, axis_y.min())
    y_max = axis_y.max()
    if y_max <= y_min:
        y_max = max((float(value) for _time, value in points), default=1.0) or 1.0

    fill = QColor(Colors.SUCCESS)
    fill.setAlpha(42)
    no_pen = QPen(Qt.PenStyle.NoPen)

    bands = []
    for window in active_windows:
        start = float(getattr(window, "StartSeconds", 0.0) or 0.0)
        end = float(getattr(window, "EndSeconds", start) or start)
        if end <= start:
            continue

        upper = QLineSeries()
        lower = QLineSeries()
        upper.append(start, y_max)
        upper.append(end, y_max)
        lower.append(start, y_min)
        lower.append(end, y_min)

        area = QAreaSeries(upper, lower)
        area.setBrush(fill)
        area.setPen(no_pen)
        chart.addSeries(area)
        area.attachAxis(axis_x)
        area.attachAxis(axis_y)
        bands.append(area)

    if not bands:
        return

    chart.removeSeries(output_series)
    chart.addSeries(output_series)
    output_series.attachAxis(axis_x)
    output_series.attachAxis(axis_y)

    page._boss_active_band_series = bands
    page.output_card.set_badge("SHADED = BOSS ACTIVE")


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from services import performance_dashboard_service as service_module
    from services.performance_boss_activity import PerformanceBossActivityService
    from widgets.performance_dashboard import PerformanceDashboard

    original_build_snapshot = service_module.PerformanceDashboardService.build_snapshot
    original_build_ui = PerformanceDashboard.build_ui
    original_update_output_chart = PerformanceDashboard._update_output_chart

    def build_snapshot_with_boss_activity(self, *args, **kwargs):
        snapshot = original_build_snapshot(self, *args, **kwargs)
        snapshot.BossActiveWindows = []
        snapshot.BossActivityTimelineError = ""

        report_code, fight_id, _actor_id, immunity_name, immunity_kind = _extract_snapshot_args(
            args, kwargs
        )
        if not str(immunity_name or "").strip():
            return snapshot

        try:
            summary = self.capability_service.fetch_fight_summary(report_code, int(fight_id))
            snapshot.BossActiveWindows = PerformanceBossActivityService(self.client).fetch_active_windows(
                report_code,
                int(fight_id),
                float(summary["start_time"]),
                float(summary["end_time"]),
                str(immunity_name),
                str(immunity_kind),
            )
        except Exception as exc:
            snapshot.BossActivityTimelineError = str(exc)

        return snapshot

    def build_ui_with_balanced_cards(self):
        original_build_ui(self)
        _balance_cards(self)

    def update_output_chart_with_boss_activity(self, points, color: str, rate_label: str):
        original_update_output_chart(self, points, color, rate_label)
        _shade_active_windows(self, points)

    service_module.PerformanceDashboardService.build_snapshot = build_snapshot_with_boss_activity
    PerformanceDashboard.build_ui = build_ui_with_balanced_cards
    PerformanceDashboard._update_output_chart = update_output_chart_with_boss_activity
    _INSTALLED = True
