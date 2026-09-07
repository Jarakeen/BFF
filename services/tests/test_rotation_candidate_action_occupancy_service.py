from __future__ import annotations

from dataclasses import dataclass

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_action_occupancy_legality_service import (
    RotationActionOccupancyRule,
)
from services.rotation_candidate_action_occupancy_service import (
    RotationCandidateActionOccupancyInput,
    RotationCandidateActionOccupancyService,
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


def _plan(*actions: RotationAction) -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="Occupancy Candidate Build",
        duration_seconds=30.0,
        actions=tuple(actions),
    )


def _upstream(
    candidate_id: str,
    plan: RotationPlan,
    *,
    eligible: bool = True,
    rank: int = 1,
) -> _ResourceResult:
    return _ResourceResult(
        candidate_id=candidate_id,
        generated_candidate=_Generated(plan),
        tier=(RotationCandidateTier.ELIGIBLE if eligible else RotationCandidateTier.INELIGIBLE),
        rank=rank,
        reasons=(f"upstream {candidate_id}",),
    )


def _heavy_rule() -> RotationActionOccupancyRule:
    return RotationActionOccupancyRule(
        action_kind=RotationActionKind.HEAVY_ATTACK,
        occupancy_seconds=2.0,
        blocked_action_kinds=(
            RotationActionKind.SKILL,
            RotationActionKind.BAR_SWAP,
        ),
        source="verified restoration heavy timing",
    )


def test_occupancy_illegal_candidate_loses_to_executable_candidate() -> None:
    illegal = _plan(
        RotationAction(5.0, 0, RotationActionKind.HEAVY_ATTACK, bar="front"),
        RotationAction(6.0, 0, RotationActionKind.SKILL, name="Combat Prayer", bar="front"),
    )
    legal = _plan(
        RotationAction(5.0, 0, RotationActionKind.HEAVY_ATTACK, bar="front"),
        RotationAction(7.0, 0, RotationActionKind.SKILL, name="Combat Prayer", bar="front"),
    )

    ranked = RotationCandidateActionOccupancyService().evaluate_and_rank(
        candidates=(
            RotationCandidateActionOccupancyInput(
                resource_result=_upstream("blocked", illegal, rank=1),
                occupancy_rules=(_heavy_rule(),),
            ),
            RotationCandidateActionOccupancyInput(
                resource_result=_upstream("executable", legal, rank=2),
                occupancy_rules=(_heavy_rule(),),
            ),
        )
    )

    assert [item.candidate_id for item in ranked] == ["executable", "blocked"]
    assert ranked[0].tier is RotationCandidateTier.ELIGIBLE
    assert ranked[1].tier is RotationCandidateTier.INELIGIBLE
    assert any("occupancy violation" in reason for reason in ranked[1].reasons)
    assert any("verified restoration heavy timing" in reason for reason in ranked[1].reasons)


def test_upstream_failure_remains_ineligible_when_occupancy_is_legal() -> None:
    plan = _plan(
        RotationAction(5.0, 0, RotationActionKind.HEAVY_ATTACK, bar="front"),
        RotationAction(7.0, 0, RotationActionKind.SKILL, name="Combat Prayer", bar="front"),
    )
    ranked = RotationCandidateActionOccupancyService().evaluate_and_rank(
        candidates=(
            RotationCandidateActionOccupancyInput(
                resource_result=_upstream("candidate", plan, eligible=False),
                occupancy_rules=(_heavy_rule(),),
            ),
        )
    )

    assert ranked[0].occupancy_assessment.is_legal is True
    assert ranked[0].tier is RotationCandidateTier.INELIGIBLE


def test_no_occupancy_evidence_preserves_upstream_order() -> None:
    plan = _plan()
    ranked = RotationCandidateActionOccupancyService().evaluate_and_rank(
        candidates=(
            RotationCandidateActionOccupancyInput(
                resource_result=_upstream("second", plan, rank=2),
            ),
            RotationCandidateActionOccupancyInput(
                resource_result=_upstream("first", plan, rank=1),
            ),
        )
    )

    assert [item.candidate_id for item in ranked] == ["first", "second"]
    assert all(item.tier is RotationCandidateTier.ELIGIBLE for item in ranked)


def test_ambiguous_occupancy_evidence_fails_candidate_closed() -> None:
    plan = _plan(
        RotationAction(3.0, 0, RotationActionKind.SKILL, name="Channel Skill", bar="front"),
    )
    generic = RotationActionOccupancyRule(
        action_kind=RotationActionKind.SKILL,
        occupancy_seconds=1.0,
        blocked_action_kinds=(RotationActionKind.BAR_SWAP,),
        source="generic skill evidence",
    )
    named = RotationActionOccupancyRule(
        action_kind=RotationActionKind.SKILL,
        action_name="Channel Skill",
        occupancy_seconds=1.5,
        blocked_action_kinds=(RotationActionKind.BAR_SWAP,),
        source="named skill evidence",
    )

    ranked = RotationCandidateActionOccupancyService().evaluate_and_rank(
        candidates=(
            RotationCandidateActionOccupancyInput(
                resource_result=_upstream("candidate", plan),
                occupancy_rules=(generic, named),
            ),
        )
    )

    assert ranked[0].tier is RotationCandidateTier.INELIGIBLE
    assert ranked[0].occupancy_assessment.violations == ()
    assert ranked[0].occupancy_assessment.unresolved
    assert any("occupancy unresolved" in reason for reason in ranked[0].reasons)


def test_duplicate_candidate_ids_fail_closed() -> None:
    plan = _plan()
    candidate = RotationCandidateActionOccupancyInput(
        resource_result=_upstream("same", plan),
    )

    try:
        RotationCandidateActionOccupancyService().evaluate_and_rank(
            candidates=(candidate, candidate),
        )
    except ValueError as exc:
        assert "duplicate rotation occupancy candidate_id" in str(exc)
    else:
        raise AssertionError("duplicate candidate IDs must fail closed")
