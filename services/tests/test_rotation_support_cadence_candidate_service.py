from __future__ import annotations

from dataclasses import dataclass

import pytest

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_duration_refinement_service import RotationDurationRefinement
from services.rotation_support_cadence_candidate_service import (
    RotationSupportCadenceCandidateService,
)
from services.rotation_support_refresh_cadence_service import (
    RotationSupportRefreshCadenceCandidate,
    RotationSupportRefreshCadenceResult,
)


@dataclass
class _RefineCall:
    plan: RotationPlan
    priorities: object
    refresh_cadences: tuple[object, ...]


class _RecordingRefiner:
    def __init__(self) -> None:
        self.calls: list[_RefineCall] = []

    def refine(self, plan, *, priorities=None, refresh_cadences=()):
        self.calls.append(
            _RefineCall(
                plan=plan,
                priorities=priorities,
                refresh_cadences=tuple(refresh_cadences),
            )
        )
        interval = refresh_cadences[0].interval_seconds
        refined = RotationPlan(
            character_name=plan.character_name,
            build_name=plan.build_name,
            duration_seconds=plan.duration_seconds,
            actions=plan.actions,
            assumptions=plan.assumptions + (f"test cadence={interval}",),
            unresolved=plan.unresolved,
        )
        return RotationDurationRefinement(
            plan=refined,
            duration_projection=None,  # type: ignore[arg-type]
        )


def _seed_plan(*, duplicate_bar: bool = False) -> RotationPlan:
    actions = [
        RotationAction(
            time_seconds=0.0,
            sequence=0,
            kind=RotationActionKind.SKILL,
            name="Combat Prayer",
            bar="front",
        ),
        RotationAction(
            time_seconds=1.0,
            sequence=0,
            kind=RotationActionKind.SKILL,
            name="Energy Orb",
            bar="back",
        ),
        RotationAction(
            time_seconds=2.0,
            sequence=0,
            kind=RotationActionKind.LIGHT_ATTACK,
            bar="front",
        ),
    ]
    if duplicate_bar:
        actions.append(
            RotationAction(
                time_seconds=3.0,
                sequence=0,
                kind=RotationActionKind.SKILL,
                name="Combat Prayer",
                bar="back",
            )
        )
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=30.0,
        actions=tuple(actions),
    )


def _cadence(
    candidate_key: str,
    interval: float,
) -> RotationSupportRefreshCadenceCandidate:
    return RotationSupportRefreshCadenceCandidate(
        candidate_key=candidate_key,
        effect_key="minor_berserk",
        source_skill_id="combat_prayer",
        recast_interval_seconds=interval,
        projected_steady_state_uptime_ratio=min(1.0, 10.0 / interval),
        effective_duration_seconds=10.0,
        target_ratio=0.90,
        rationale=f"test {candidate_key}",
    )


def _result(*candidates: RotationSupportRefreshCadenceCandidate):
    return RotationSupportRefreshCadenceResult(
        effect_key="minor_berserk",
        source_skill_id="combat_prayer",
        candidates=tuple(candidates),
    )


def test_materializes_each_cadence_as_a_complete_refined_plan() -> None:
    seed = _seed_plan()
    refiner = _RecordingRefiner()
    service = RotationSupportCadenceCandidateService(refiner)

    candidates = service.materialize(
        seed_plan=seed,
        cadence_result=_result(
            _cadence("full_coverage", 10.0),
            _cadence("target_floor", 10.0 / 0.90),
        ),
    )

    assert [candidate.candidate_id for candidate in candidates] == [
        "minor_berserk:combat_prayer:full_coverage:front",
        "minor_berserk:combat_prayer:target_floor:front",
    ]
    assert len(refiner.calls) == 2
    assert all(call.plan is seed for call in refiner.calls)
    assert all(candidate.plan.actions == seed.actions for candidate in candidates)
    assert all(
        any(action.name == "Energy Orb" for action in candidate.plan.actions)
        for candidate in candidates
    )
    assert candidates[0].plan.assumptions[-1] == "test cadence=10.0"
    assert candidates[1].plan.assumptions[-1].startswith("test cadence=11.111")


def test_semantic_skill_id_resolves_to_exact_seed_plan_name_and_bar() -> None:
    refiner = _RecordingRefiner()
    service = RotationSupportCadenceCandidateService(refiner)

    candidate = service.materialize(
        seed_plan=_seed_plan(),
        cadence_result=_result(_cadence("full_coverage", 10.0)),
    )[0]

    policy = candidate.refresh_policy
    assert policy.skill_name == "Combat Prayer"
    assert policy.bar == "front"
    assert policy.interval_seconds == pytest.approx(10.0)
    assert policy.source == "support cadence candidate minor_berserk:full_coverage"


def test_same_skill_on_two_bars_requires_explicit_bar_disambiguation() -> None:
    service = RotationSupportCadenceCandidateService(_RecordingRefiner())

    with pytest.raises(ValueError, match="ambiguous.*source_bar is required"):
        service.materialize(
            seed_plan=_seed_plan(duplicate_bar=True),
            cadence_result=_result(_cadence("full_coverage", 10.0)),
        )


def test_explicit_bar_disambiguates_same_semantic_skill() -> None:
    refiner = _RecordingRefiner()
    service = RotationSupportCadenceCandidateService(refiner)

    candidate = service.materialize(
        seed_plan=_seed_plan(duplicate_bar=True),
        cadence_result=_result(_cadence("full_coverage", 10.0)),
        source_bar="back",
    )[0]

    assert candidate.refresh_policy.skill_name == "Combat Prayer"
    assert candidate.refresh_policy.bar == "back"


def test_missing_source_skill_is_rejected_instead_of_guessed() -> None:
    service = RotationSupportCadenceCandidateService(_RecordingRefiner())
    missing = RotationSupportRefreshCadenceResult(
        effect_key="minor_berserk",
        source_skill_id="not_on_the_bar",
        candidates=(
            RotationSupportRefreshCadenceCandidate(
                candidate_key="full_coverage",
                effect_key="minor_berserk",
                source_skill_id="not_on_the_bar",
                recast_interval_seconds=10.0,
                projected_steady_state_uptime_ratio=1.0,
                effective_duration_seconds=10.0,
                target_ratio=1.0,
                rationale="test",
            ),
        ),
    )

    with pytest.raises(ValueError, match="is not present in the seed plan"):
        service.materialize(seed_plan=_seed_plan(), cadence_result=missing)


def test_unresolved_or_empty_cadence_result_creates_no_plan_candidates() -> None:
    refiner = _RecordingRefiner()
    service = RotationSupportCadenceCandidateService(refiner)
    result = RotationSupportRefreshCadenceResult(
        effect_key="minor_berserk",
        source_skill_id="combat_prayer",
        candidates=(),
        unresolved=("duration evidence missing",),
    )

    assert service.materialize(seed_plan=_seed_plan(), cadence_result=result) == ()
    assert refiner.calls == []


def test_two_bar_healer_cadence_neighborhood_has_distinct_complete_plans():
    """Both legal bar alternatives survive materialization without ID collisions.

    Durations here are explicit fixture evidence, not current ESO tooltip claims.
    The real local scheduler keeps unrelated heals and the other bar's casts.
    """
    from minmax.rotation_recast import RotationRecastAnalysis, RotationRecastRule
    from services.rotation_duration_analysis_service import RotationDurationProjection
    from services.rotation_local_cadence_duration_refinement_service import (
        RotationLocalCadenceDurationRefinementService,
    )
    from services.rotation_support_cadence_neighborhood_service import (
        RotationSupportCadenceNeighborhoodObligation,
        RotationSupportCadenceNeighborhoodService,
    )

    class DurationAnalysis:
        def analyze(self, plan):
            return RotationDurationProjection(
                analysis=RotationRecastAnalysis(windows=(), summaries=()),
                rules=(
                    RotationRecastRule("Combat Prayer", 10.0, bar="front"),
                    RotationRecastRule("Combat Prayer", 10.0, bar="back"),
                    RotationRecastRule("Energy Orb", 10.0, bar="back"),
                    RotationRecastRule("Illustrious Healing", 10.0, bar="front"),
                ),
                unresolved=(),
            )

    actions = []
    for start in (0.0, 10.0, 20.0):
        actions.extend((
            RotationAction(start, 0, RotationActionKind.SKILL, "Combat Prayer", "front"),
            RotationAction(start + 1, 0, RotationActionKind.SKILL, "Illustrious Healing", "front"),
            RotationAction(start + 2, 0, RotationActionKind.BAR_SWAP, bar="back"),
            RotationAction(start + 3, 0, RotationActionKind.SKILL, "Combat Prayer", "back"),
            RotationAction(start + 4, 0, RotationActionKind.SKILL, "Energy Orb", "back"),
            RotationAction(start + 5, 0, RotationActionKind.LIGHT_ATTACK, bar="back"),
            RotationAction(start + 6, 0, RotationActionKind.BAR_SWAP, bar="front"),
        ))
    seed = RotationPlan("Healer", "Two restoration bars", 30.0, tuple(actions))
    materializer = RotationSupportCadenceCandidateService(
        RotationLocalCadenceDurationRefinementService(duration_analysis=DurationAnalysis())
    )
    neighborhood = RotationSupportCadenceNeighborhoodService(materializer)
    obligations = tuple(
        RotationSupportCadenceNeighborhoodObligation(
            _result(_cadence("target_floor", 20.0)), source_bar=bar,
        )
        for bar in ("front", "back")
    )
    result = neighborhood.generate(seed_plan=seed, obligations=obligations)
    again = neighborhood.generate(seed_plan=seed, obligations=obligations)

    assert len(result.candidates) == 2
    assert [c.candidate_id for c in result.candidates] == [
        "minor_berserk:combat_prayer:target_floor:front",
        "minor_berserk:combat_prayer:target_floor:back",
    ]
    assert [c.plan for c in again.candidates] == [c.plan for c in result.candidates]
    for candidate in result.candidates:
        changed_bar = candidate.refresh_policy.bar
        other_bar = "back" if changed_bar == "front" else "front"
        preserved = lambda action: (
            action.name in {"Energy Orb", "Illustrious Healing"}
            or (action.name == "Combat Prayer" and action.bar == other_bar)
            or action.kind in {RotationActionKind.BAR_SWAP, RotationActionKind.LIGHT_ATTACK}
        )
        assert tuple(filter(preserved, candidate.plan.actions)) == tuple(filter(preserved, seed.actions))
        times = [a.time_seconds for a in candidate.plan.actions
                 if a.name == "Combat Prayer" and a.bar == changed_bar]
        assert times == ([0.0, 20.0] if changed_bar == "front" else [3.0, 23.0])
        assert candidate.plan.character_name == seed.character_name
        assert candidate.plan.build_name == seed.build_name
        assert candidate.plan.duration_seconds == seed.duration_seconds
    assert seed.actions == tuple(actions)


def test_implicit_and_explicit_source_bar_have_same_candidate_identity():
    service = RotationSupportCadenceCandidateService(_RecordingRefiner())
    kwargs = dict(seed_plan=_seed_plan(), cadence_result=_result(_cadence("full_coverage", 10.0)))
    implicit = service.materialize(**kwargs)[0]
    explicit = service.materialize(**kwargs, source_bar=" FRONT ")[0]
    assert implicit.candidate_id == explicit.candidate_id
