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

    def build_snapshot_with_effect_windows(self, *args, **kwargs):
        """Preserve the wrapped service's call contract exactly.

        Performance Dashboard has several compatibility layers on the shared
        branch. Some callers/wrappers add keyword-only options over time. This
        timeline layer must therefore be transparent: accept and forward the
        complete call rather than freezing an older build_snapshot signature.
        """
        snapshot = original_build_snapshot(self, *args, **kwargs)

        # Resolve the three values this layer itself needs without constraining
        # the wrapped method's remaining positional/keyword arguments.
        report_code = kwargs.get("report_code", args[0] if len(args) > 0 else "")
        fight_id = kwargs.get("fight_id", args[1] if len(args) > 1 else None)
        actor_id = kwargs.get("actor_id", args[2] if len(args) > 2 else None)

        # Timeline failure should not throw away the already-valid aggregate
        # dashboard. Keep the error inspectable for the UI instead.
        snapshot.EffectWindows = []
        snapshot.EffectTimelineError = ""

        if not report_code or fight_id is None or actor_id is None:
            snapshot.EffectTimelineError = (
                "Timeline context was unavailable after building the aggregate dashboard."
            )
            return snapshot

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
