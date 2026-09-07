from __future__ import annotations

from dataclasses import dataclass

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_action_occupancy_legality_service import RotationActionOccupancyRule
from services.rotation_build_timing_projection_service import (
    RotationBuildTimingPolicy,
    RotationBuildTimingProjection,
)
from services.rotation_candidate_build_timing_service import (
    RotationCandidateBuildTimingInput,
    RotationCandidateBuildTimingService,
)
from services.rotation_candidate_ranking_service import RotationCandidateTier


@dataclass(frozen=True)
class _Generated:
    plan: RotationPlan


@dataclass(frozen=True)
class _ResourceResult:
    candidate_id: str
    generated_candidate: _Generated
    tier: RotationCandidateTier
    rank: int
    reasons: tuple[str, ...]


class _ProjectionService:
    def __init__(self, projection: RotationBuildTimingProjection) -> None:
        self.projection = projection
        self.calls = 0

    def project(self, *, build, policy):
        self.calls += 1
        return self.projection


def _plan(*actions: RotationAction) -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="Build Timing Candidate",
        duration_seconds=30.0,
        actions=tuple(actions),
    )


def _resource(candidate_id: str, plan: RotationPlan, *, eligible: bool = True, rank: int = 1):
    return _ResourceResult(
        candidate_id=candidate_id,
        generated_candidate=_Generated(plan),
        tier=RotationCandidateTier.ELIGIBLE if eligible else RotationCandidateTier.INELIGIBLE,
        rank=rank,
        reasons=(f"resource {candidate_id}",),
    )


def _projection(*, unresolved=()):
    return RotationBuildTimingProjection(
        build_name="Build Timing Candidate",
        evidence=(),
        rules=(
            RotationActionOccupancyRule(
                action_kind=RotationActionKind.SKILL,
                action_name="Channel Skill",
                occupancy_seconds=2.0,
                blocked_action_kinds=(RotationActionKind.SKILL,),
                source="canonical fixture timing",
            ),
        ),
        unresolved=tuple(unresolved),
    )


def _service(projection: RotationBuildTimingProjection):
    projector = _ProjectionService(projection)
    service = RotationCandidateBuildTimingService(
        database_path="unused.db",
        projection_service=projector,
    )
    return service, projector


def test_build_timing_rules_are_applied_automatically_to_every_candidate() -> None:
    service, projector = _service(_projection())
    blocked = _plan(
        RotationAction(0.0, 0, RotationActionKind.SKILL, name="Channel Skill", bar="front"),
        RotationAction(1.0, 0, RotationActionKind.SKILL, name="Next Skill", bar="front"),
    )
    legal = _plan(
        RotationAction(0.0, 0, RotationActionKind.SKILL, name="Channel Skill", bar="front"),
        RotationAction(2.0, 0, RotationActionKind.SKILL, name="Next Skill", bar="front"),
    )

    ranked = service.evaluate_and_rank(
        build=object(),
        policy=RotationBuildTimingPolicy(),
        candidates=(
            RotationCandidateBuildTimingInput(_resource("blocked", blocked, rank=1)),
            RotationCandidateBuildTimingInput(_resource("legal", legal, rank=2)),
        ),
    )

    assert projector.calls == 1
    assert [item.candidate_id for item in ranked] == ["legal", "blocked"]
    assert ranked[0].tier is RotationCandidateTier.ELIGIBLE
    assert ranked[1].tier is RotationCandidateTier.INELIGIBLE
    assert any("occupancy violation" in reason for reason in ranked[1].reasons)


def test_unresolved_build_timing_is_a_hard_failure_not_zero_occupancy() -> None:
    service, _projector = _service(
        _projection(unresolved=("front bar skill 'Mystery Skill': canonical timing unresolved",))
    )

    ranked = service.evaluate_and_rank(
        build=object(),
        policy=RotationBuildTimingPolicy(),
        candidates=(
            RotationCandidateBuildTimingInput(_resource("candidate", _plan())),
        ),
    )

    assert ranked[0].occupancy_result.occupancy_assessment.is_legal is True
    assert ranked[0].tier is RotationCandidateTier.INELIGIBLE
    assert any("build timing projection unresolved" in reason for reason in ranked[0].reasons)
    assert any("Mystery Skill" in reason for reason in ranked[0].reasons)


def test_upstream_hard_failure_remains_ineligible_with_clean_build_timing() -> None:
    service, _projector = _service(_projection())

    ranked = service.evaluate_and_rank(
        build=object(),
        policy=RotationBuildTimingPolicy(),
        candidates=(
            RotationCandidateBuildTimingInput(
                _resource("candidate", _plan(), eligible=False)
            ),
        ),
    )

    assert ranked[0].occupancy_result.occupancy_assessment.is_legal is True
    assert ranked[0].tier is RotationCandidateTier.INELIGIBLE


def test_clean_build_timing_preserves_existing_candidate_order() -> None:
    service, _projector = _service(_projection())

    ranked = service.evaluate_and_rank(
        build=object(),
        policy=RotationBuildTimingPolicy(),
        candidates=(
            RotationCandidateBuildTimingInput(_resource("second", _plan(), rank=2)),
            RotationCandidateBuildTimingInput(_resource("first", _plan(), rank=1)),
        ),
    )

    assert [item.candidate_id for item in ranked] == ["first", "second"]
    assert all(item.tier is RotationCandidateTier.ELIGIBLE for item in ranked)


def test_duplicate_candidate_ids_fail_closed_before_ranking() -> None:
    service, _projector = _service(_projection())
    candidate = RotationCandidateBuildTimingInput(_resource("same", _plan()))

    try:
        service.evaluate_and_rank(
            build=object(),
            policy=RotationBuildTimingPolicy(),
            candidates=(candidate, candidate),
        )
    except ValueError as exc:
        assert "duplicate rotation build-timing candidate_id" in str(exc)
    else:
        raise AssertionError("duplicate candidate IDs must fail closed")
