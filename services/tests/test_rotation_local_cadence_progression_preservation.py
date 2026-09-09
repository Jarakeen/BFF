from __future__ import annotations

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.rotation_recast import RotationRecastAnalysis, RotationRecastRule
from services.rotation_duration_analysis_service import RotationDurationProjection
from services.rotation_local_cadence_duration_refinement_service import (
    RotationLocalCadenceDurationRefinementService,
)
from services.rotation_support_cadence_candidate_service import (
    RotationSupportCadenceCandidateService,
)
from services.rotation_support_refresh_cadence_service import (
    RotationSupportRefreshCadenceCandidate,
    RotationSupportRefreshCadenceResult,
)


class _DurationAnalysis:
    def __init__(self) -> None:
        self.rules = (
            RotationRecastRule("Effect A", 10.0, bar="front"),
            RotationRecastRule("Effect B", 10.0, bar="front"),
        )

    def analyze(self, plan: RotationPlan) -> RotationDurationProjection:
        return RotationDurationProjection(
            analysis=RotationRecastAnalysis(windows=(), summaries=()),
            rules=self.rules,
            unresolved=(),
        )


def _skill(time_seconds: float, name: str) -> RotationAction:
    return RotationAction(
        time_seconds=time_seconds,
        sequence=1,
        kind=RotationActionKind.SKILL,
        name=name,
        bar="front",
    )


def _seed() -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=40.0,
        actions=(
            _skill(0.0, "Effect A"),
            _skill(1.0, "Effect B"),
            _skill(5.0, "Filler"),
            _skill(10.0, "Effect A"),
            _skill(11.0, "Effect B"),
            _skill(15.0, "Filler"),
            _skill(20.0, "Effect A"),
            _skill(21.0, "Effect B"),
            _skill(25.0, "Filler"),
            _skill(30.0, "Effect A"),
            _skill(31.0, "Effect B"),
            _skill(35.0, "Filler"),
        ),
    )


def _cadence(
    *,
    effect_key: str,
    source_skill_id: str,
    interval: float,
) -> RotationSupportRefreshCadenceResult:
    candidate = RotationSupportRefreshCadenceCandidate(
        candidate_key="test",
        effect_key=effect_key,
        source_skill_id=source_skill_id,
        recast_interval_seconds=interval,
        projected_steady_state_uptime_ratio=min(1.0, 10.0 / interval),
        effective_duration_seconds=10.0,
        target_ratio=min(1.0, 10.0 / interval),
        rationale="test cadence",
    )
    return RotationSupportRefreshCadenceResult(
        effect_key=effect_key,
        source_skill_id=source_skill_id,
        candidates=(candidate,),
    )


def _times(plan: RotationPlan, name: str) -> list[float]:
    return [
        action.time_seconds
        for action in plan.actions
        if action.kind is RotationActionKind.SKILL and action.name == name
    ]


def test_second_cadence_candidate_preserves_first_accepted_local_schedule() -> None:
    refiner = RotationLocalCadenceDurationRefinementService(
        duration_analysis=_DurationAnalysis()
    )
    materializer = RotationSupportCadenceCandidateService(refiner)

    a_candidate = materializer.materialize(
        seed_plan=_seed(),
        cadence_result=_cadence(
            effect_key="effect_a",
            source_skill_id="effect_a",
            interval=15.0,
        ),
        source_bar="front",
    )[0]

    assert _times(a_candidate.plan, "Effect A") == [0.0, 15.0, 30.0]

    b_candidate = materializer.materialize(
        seed_plan=a_candidate.plan,
        cadence_result=_cadence(
            effect_key="effect_b",
            source_skill_id="effect_b",
            interval=20.0,
        ),
        source_bar="front",
    )[0]

    assert _times(b_candidate.plan, "Effect A") == [0.0, 15.0, 30.0]
    assert _times(b_candidate.plan, "Effect B") == [1.0, 21.0]

    # The second candidate remains a one-change neighborhood member. It does not
    # reconstruct Effect A from its canonical 10-second duration or combine cadence
    # families as a Cartesian product.
    assert b_candidate.candidate_id == "effect_b:effect_b:test"
