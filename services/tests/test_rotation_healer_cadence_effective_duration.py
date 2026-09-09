"""Synthetic healer duration evidence through real local cadence scheduling.

Fixture values are explicit inputs, not claims about current ESO tooltips.
"""
from types import SimpleNamespace

from minmax.refresh_cadence_duration_scheduler import RotationRefreshIntervalPolicy
from minmax.rotation_effective_duration import RotationEffectiveDurationOverride
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_duration_analysis_service import RotationDurationAnalysisService
from services.rotation_local_cadence_duration_refinement_service import RotationLocalCadenceDurationRefinementService
from ui.rotation_support_cadence_runtime_support import build_rotation_support_cadence_progression_runner


class _Repository:
    def resolve_name(self, name):
        return SimpleNamespace(skill_name=name, duration_seconds=10.0 if name == "Combat Prayer" else None, unresolved=())


def _seed():
    return RotationPlan(
        "Healer", "Duration extension fixture", 60.0,
        tuple(RotationAction(float(t), 0,
            RotationActionKind.SKILL,
            "Combat Prayer" if t % 10 == 0 else "Fixture filler", "front")
            for t in range(60)),
    )


def _override(bar="front"):
    return RotationEffectiveDurationOverride("Combat Prayer", 26.0, "reviewed fixture extension", bar)


def _refiner(overrides=()):
    return RotationLocalCadenceDurationRefinementService(
        duration_analysis=RotationDurationAnalysisService(duration_repository=_Repository()),
        effective_duration_overrides=overrides,
    )


def _refine(service, plan=None, interval=26.0):
    return service.refine(_seed() if plan is None else plan, refresh_cadences=(
        RotationRefreshIntervalPolicy("Combat Prayer", interval, bar="front", source="fixture strategy"),
    ))


def test_build_extension_survives_initial_and_final_cadence_analysis():
    evidence = _override()
    result = _refine(_refiner((evidence,)))
    assert [a.time_seconds for a in result.plan.actions if a.name == "Combat Prayer"] == [0.0, 26.0, 52.0]
    summary = result.duration_projection.analysis.summaries[0]
    assert summary.duration_seconds == 26.0
    assert summary.uptime_fraction == 1.0
    assert result.duration_projection.effective_duration_overrides == (evidence,)


def test_strategic_gap_does_not_change_mechanical_duration():
    result = _refine(_refiner((_override(),)), interval=30.0)
    summary = result.duration_projection.analysis.summaries[0]
    assert summary.duration_seconds == 26.0
    assert summary.active_seconds == 52.0
    assert summary.uptime_fraction == 52.0 / 60.0


def test_extension_survives_repeated_local_refinement():
    service = _refiner((_override(),))
    first = _refine(service)
    second = _refine(service, first.plan)
    assert second.plan.actions == first.plan.actions
    assert second.duration_projection.effective_duration_overrides == first.duration_projection.effective_duration_overrides
    assert second.duration_projection.analysis.summaries[0].duration_seconds == 26.0


def test_other_bar_extension_does_not_leak_into_front_bar():
    result = _refine(_refiner((_override("back"),)))
    assert result.duration_projection.analysis.summaries[0].duration_seconds == 10.0
    assert result.duration_projection.effective_duration_overrides == ()


def test_without_extension_preserves_base_duration():
    result = _refine(_refiner())
    assert result.duration_projection.analysis.summaries[0].duration_seconds == 10.0
    assert result.duration_projection.analysis.summaries[0].uptime_fraction < 1.0


def test_production_runner_carries_build_duration_evidence():
    evidence = _override()
    runner = build_rotation_support_cadence_progression_runner(effective_duration_overrides=(evidence,))
    refiner = runner.progression_service.neighborhood_service.materializer.duration_refiner
    assert refiner.effective_duration_overrides == (evidence,)


def test_duplicate_duration_evidence_is_rejected_before_scheduling():
    try:
        _refiner((_override(), _override()))
    except ValueError as error:
        assert "duplicate effective rotation duration" in str(error)
    else:
        raise AssertionError("duplicate duration evidence was accepted")
