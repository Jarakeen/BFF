from __future__ import annotations

from dataclasses import dataclass

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.ultimate_resource_timeline import UltimateGenerationEvent, UltimateSpendRule
from services.rotation_candidate_ranking_service import RotationCandidateTier
from services.rotation_candidate_resource_legality_service import (
    RotationCandidateResourceLegalityInput,
    RotationCandidateResourceLegalityService,
)


@dataclass(frozen=True)
class _Generated:
    plan: RotationPlan


@dataclass(frozen=True)
class _LegalityResult:
    candidate_id: str
    generated_candidate: _Generated
    tier: RotationCandidateTier
    rank: int
    reasons: tuple[str, ...]


def _plan(*actions: RotationAction) -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="Resource Legality Build",
        duration_seconds=60.0,
        actions=tuple(actions),
    )


def _upstream(
    candidate_id: str,
    plan: RotationPlan,
    *,
    eligible: bool = True,
    rank: int = 1,
) -> _LegalityResult:
    return _LegalityResult(
        candidate_id=candidate_id,
        generated_candidate=_Generated(plan),
        tier=(
            RotationCandidateTier.ELIGIBLE
            if eligible
            else RotationCandidateTier.INELIGIBLE
        ),
        rank=rank,
        reasons=(f"upstream {candidate_id}",),
    )


def _horn(time: float, sequence: int = 0) -> RotationAction:
    return RotationAction(
        time_seconds=time,
        sequence=sequence,
        kind=RotationActionKind.ULTIMATE,
        name="Aggressive Horn",
        bar="front",
    )


def _potion(time: float, sequence: int = 0) -> RotationAction:
    return RotationAction(
        time_seconds=time,
        sequence=sequence,
        kind=RotationActionKind.POTION,
        name="Essence of Spell Power",
        bar="front",
    )


def _horn_rule(cost: float = 250.0) -> UltimateSpendRule:
    return UltimateSpendRule(skill_name="Aggressive Horn", cost=cost)


def test_resource_illegal_candidate_loses_to_affordable_candidate() -> None:
    service = RotationCandidateResourceLegalityService()
    plan = _plan(_horn(10.0))

    ranked = service.evaluate_and_rank(
        candidates=(
            RotationCandidateResourceLegalityInput(
                legality_result=_upstream("cannot-pay", plan, rank=1),
                starting_ultimate=100.0,
                ultimate_spend_rules=(_horn_rule(),),
            ),
            RotationCandidateResourceLegalityInput(
                legality_result=_upstream("can-pay", plan, rank=2),
                starting_ultimate=250.0,
                ultimate_spend_rules=(_horn_rule(),),
            ),
        )
    )

    assert [item.candidate_id for item in ranked] == ["can-pay", "cannot-pay"]
    assert ranked[0].tier is RotationCandidateTier.ELIGIBLE
    assert ranked[1].tier is RotationCandidateTier.INELIGIBLE
    assert ranked[0].resource_legality.ending_ultimate == 0.0
    assert any("requires 250.000 Ultimate" in reason for reason in ranked[1].reasons)


def test_generation_before_cast_can_make_candidate_legal() -> None:
    plan = _plan(_horn(20.0))
    ranked = RotationCandidateResourceLegalityService().evaluate_and_rank(
        candidates=(
            RotationCandidateResourceLegalityInput(
                legality_result=_upstream("candidate", plan),
                starting_ultimate=100.0,
                ultimate_generation_events=(
                    UltimateGenerationEvent(10.0, 150.0, "verified generation"),
                ),
                ultimate_spend_rules=(_horn_rule(),),
            ),
        )
    )

    assert ranked[0].tier is RotationCandidateTier.ELIGIBLE
    assert ranked[0].resource_legality.is_legal is True
    assert ranked[0].resource_legality.ending_ultimate == 0.0


def test_same_timestamp_ultimate_affordability_unresolved_is_hard_failure() -> None:
    plan = _plan(_horn(10.0))
    ranked = RotationCandidateResourceLegalityService().evaluate_and_rank(
        candidates=(
            RotationCandidateResourceLegalityInput(
                legality_result=_upstream("candidate", plan),
                starting_ultimate=200.0,
                ultimate_generation_events=(
                    UltimateGenerationEvent(10.0, 50.0, "same-time gain"),
                ),
                ultimate_spend_rules=(_horn_rule(),),
            ),
        )
    )

    assert ranked[0].tier is RotationCandidateTier.INELIGIBLE
    assert ranked[0].resource_legality.violations == ()
    assert ranked[0].resource_legality.unresolved
    assert any("same-timestamp generation occurs first" in reason for reason in ranked[0].reasons)


def test_potion_cooldown_failure_is_hard_candidate_failure() -> None:
    plan = _plan(_potion(0.0), _potion(30.0, 1))
    ranked = RotationCandidateResourceLegalityService().evaluate_and_rank(
        candidates=(
            RotationCandidateResourceLegalityInput(
                legality_result=_upstream("candidate", plan),
            ),
        )
    )

    assert ranked[0].tier is RotationCandidateTier.INELIGIBLE
    assert any("inside the 45.000s cooldown" in reason for reason in ranked[0].reasons)


def test_upstream_failure_remains_ineligible_when_resources_are_legal() -> None:
    plan = _plan(_horn(10.0))
    ranked = RotationCandidateResourceLegalityService().evaluate_and_rank(
        candidates=(
            RotationCandidateResourceLegalityInput(
                legality_result=_upstream("candidate", plan, eligible=False),
                starting_ultimate=250.0,
                ultimate_spend_rules=(_horn_rule(),),
            ),
        )
    )

    assert ranked[0].resource_legality.is_legal is True
    assert ranked[0].tier is RotationCandidateTier.INELIGIBLE


def test_no_resource_actions_preserves_upstream_order() -> None:
    plan = _plan()
    ranked = RotationCandidateResourceLegalityService().evaluate_and_rank(
        candidates=(
            RotationCandidateResourceLegalityInput(
                legality_result=_upstream("second", plan, rank=2),
            ),
            RotationCandidateResourceLegalityInput(
                legality_result=_upstream("first", plan, rank=1),
            ),
        )
    )

    assert [item.candidate_id for item in ranked] == ["first", "second"]
    assert all(item.tier is RotationCandidateTier.ELIGIBLE for item in ranked)


def test_duplicate_candidate_ids_fail_closed() -> None:
    plan = _plan()
    candidate = RotationCandidateResourceLegalityInput(
        legality_result=_upstream("same", plan),
    )

    try:
        RotationCandidateResourceLegalityService().evaluate_and_rank(
            candidates=(candidate, candidate),
        )
    except ValueError as exc:
        assert "duplicate rotation resource-legality candidate_id" in str(exc)
    else:
        raise AssertionError("duplicate candidate IDs must fail closed")
