from __future__ import annotations

"""Attach exact ESO Logs aura windows to fresh PerformanceSnapshots.

The canonical snapshot contract predates timeline lanes, so this compatibility
layer adds an ``EffectWindows`` attribute after the normal snapshot has been
built. Aggregate uptime remains the fallback if the event query is unavailable.
"""

_INSTALLED = False


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from services import performance_dashboard_service as service_module
    from services.performance_effect_timeline import PerformanceEffectTimelineService

    original_build_snapshot = service_module.PerformanceDashboardService.build_snapshot

    def build_snapshot_with_effect_windows(
        self,
        report_code: str,
        fight_id: int,
        actor_id: int,
        actor_label: str,
        role: str,
        immunity_buff_name: str = "",
        immunity_buff_kind: str = "Buff",
    ):
        snapshot = original_build_snapshot(
            self,
            report_code,
            fight_id,
            actor_id,
            actor_label,
            role,
            immunity_buff_name,
            immunity_buff_kind,
        )

        # Timeline failure should not throw away the already-valid aggregate
        # dashboard. Keep the error inspectable for the UI instead.
        snapshot.EffectWindows = []
        snapshot.EffectTimelineError = ""
        try:
            summary = self.capability_service.fetch_fight_summary(report_code, fight_id)
            start_ms = float(summary["start_time"])
            end_ms = float(summary["end_time"])
            snapshot.EffectWindows = PerformanceEffectTimelineService(self.client).fetch_windows(
                report_code,
                int(fight_id),
                int(actor_id),
                start_ms,
                end_ms,
            )
        except Exception as exc:
            snapshot.EffectTimelineError = str(exc)

        return snapshot

    service_module.PerformanceDashboardService.build_snapshot = build_snapshot_with_effect_windows
    _INSTALLED = True
