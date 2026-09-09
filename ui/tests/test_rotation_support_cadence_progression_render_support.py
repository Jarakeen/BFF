from types import SimpleNamespace

from minmax.rotation_plan import RotationPlan
from ui.rotation_support_cadence_progression_render_support import (
    RotationSupportCadenceProgressionRenderSupport,
)


def _plan(name: str) -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name=name,
        duration_seconds=30.0,
        actions=(),
    )


class _DurationEvidence:
    def __init__(self) -> None:
        self.calls = []

    def build(self, plan):
        self.calls.append(plan)
        return SimpleNamespace(source_plan=plan)


class _ReportService:
    def __init__(self, report) -> None:
        self.report = report
        self.calls = []

    def build(self, run):
        self.calls.append(run)
        return self.report


def test_render_support_uses_final_accepted_plan_sustain_and_report_together() -> None:
    initial = _plan("Seed")
    final = _plan("Accepted Final")
    final_sustain = object()
    run = SimpleNamespace(
        initial_plan=initial,
        final_plan=final,
        final_sustain=final_sustain,
    )
    duration = _DurationEvidence()
    report = SimpleNamespace(stop_summary="No further improvement.")
    reports = _ReportService(report)
    support = RotationSupportCadenceProgressionRenderSupport(
        duration_evidence=duration,
        report_service=reports,
    )

    evidence = support.build(run)  # type: ignore[arg-type]

    assert evidence.plan is final
    assert evidence.plan is not initial
    assert evidence.sustain_projection is final_sustain
    assert evidence.duration_evidence.source_plan is final
    assert evidence.report is report
    assert duration.calls == [final]
    assert reports.calls == [run]


def test_render_support_does_not_mutate_or_reselect_progression_result() -> None:
    final = _plan("Final")
    run = SimpleNamespace(final_plan=final, final_sustain=object())
    duration = _DurationEvidence()
    reports = _ReportService(SimpleNamespace())
    support = RotationSupportCadenceProgressionRenderSupport(
        duration_evidence=duration,
        report_service=reports,
    )

    first = support.build(run)  # type: ignore[arg-type]
    second = support.build(run)  # type: ignore[arg-type]

    assert first.plan is final
    assert second.plan is final
    assert duration.calls == [final, final]
    assert reports.calls == [run, run]
