from __future__ import annotations

import pytest

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_candidate_action_damage_evidence_service import (
    RotationCandidateActionDamageEvidenceService,
)
from services.rotation_candidate_dd_role_output_service import (
    RotationActionDamageEvidence,
    RotationCandidateDDRoleOutputService,
)
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_candidate_ultimate_damage_evidence_service import (
    RotationCandidateUltimateDamageEvidenceService,
)


def _candidate(*actions: RotationAction) -> GeneratedRotationCandidate:
    return GeneratedRotationCandidate(
        candidate_id="ultimate-candidate",
        plan=RotationPlan(
            character_name="Damage Tester",
            build_name="Ultimate Build",
            duration_seconds=10.0,
            actions=tuple(actions),
        ),
        refresh_leads=(),
        action_claims=(),
    )


class _SkillDamageDelegate:
    def __init__(self, *, damage=5000.0, unresolved=()) -> None:
        self.damage = damage
        self.unresolved = tuple(unresolved)
        self.calls = []

    def evaluate_action(self, *, candidate, action):
        self.calls.append((candidate, action))
        return RotationActionDamageEvidence(
            time_seconds=action.time_seconds,
            sequence=action.sequence,
            damage_value=None if self.unresolved else self.damage,
            unresolved=self.unresolved,
        )


class _MismatchedDelegate:
    def evaluate_action(self, *, candidate, action):
        return RotationActionDamageEvidence(
            time_seconds=action.time_seconds + 1.0,
            sequence=action.sequence,
            damage_value=1000.0,
        )


def test_ultimate_routes_same_identity_and_schedule_through_skill_damage_authority() -> None:
    ultimate = RotationAction(
        4.0,
        7,
        RotationActionKind.ULTIMATE,
        name="wild_guardian",
        bar="front",
    )
    candidate = _candidate(ultimate)
    delegate = _SkillDamageDelegate(damage=5000.0)
    service = RotationCandidateUltimateDamageEvidenceService(
        skill_damage_delegate=delegate,
    )

    evidence = service.evaluate_action(candidate=candidate, action=ultimate)

    assert evidence.damage_value == 5000.0
    assert evidence.unresolved == ()
    assert len(delegate.calls) == 1
    delegated_candidate, delegated_action = delegate.calls[0]
    assert delegated_candidate is candidate
    assert delegated_action.kind is RotationActionKind.SKILL
    assert delegated_action.name == "wild_guardian"
    assert delegated_action.time_seconds == 4.0
    assert delegated_action.sequence == 7
    assert delegated_action.bar == "front"


def test_ultimate_damage_contributes_to_whole_plan_dd_output_through_dispatcher() -> None:
    ultimate = RotationAction(
        2.0,
        3,
        RotationActionKind.ULTIMATE,
        name="standard_of_might",
        bar="back",
    )
    candidate = _candidate(ultimate)
    ultimate_provider = RotationCandidateUltimateDamageEvidenceService(
        skill_damage_delegate=_SkillDamageDelegate(damage=12000.0),
    )
    router = RotationCandidateActionDamageEvidenceService(
        ultimate_provider=ultimate_provider,
    )

    output = RotationCandidateDDRoleOutputService(
        action_damage_evidence_provider=router,
    ).evaluate_plan(candidate)

    assert output.unresolved == ()
    assert output.value == pytest.approx(1200.0)


def test_unresolved_skill_damage_propagates_through_ultimate_adapter() -> None:
    ultimate = RotationAction(
        0.0,
        0,
        RotationActionKind.ULTIMATE,
        name="periodic_ultimate",
        bar="front",
    )
    candidate = _candidate(ultimate)
    service = RotationCandidateUltimateDamageEvidenceService(
        skill_damage_delegate=_SkillDamageDelegate(
            unresolved=(
                "periodic Ultimate component requires Ultimate-aware runtime projection",
            )
        ),
    )

    evidence = service.evaluate_action(candidate=candidate, action=ultimate)

    assert evidence.damage_value is None
    assert evidence.unresolved == (
        "periodic Ultimate component requires Ultimate-aware runtime projection",
    )


def test_non_ultimate_action_is_not_relabelled_as_ultimate_damage() -> None:
    skill = RotationAction(
        0.0,
        0,
        RotationActionKind.SKILL,
        name="deep_fissure",
        bar="front",
    )
    delegate = _SkillDamageDelegate()
    service = RotationCandidateUltimateDamageEvidenceService(
        skill_damage_delegate=delegate,
    )

    evidence = service.evaluate_action(candidate=_candidate(skill), action=skill)

    assert evidence.damage_value is None
    assert evidence.unresolved == (
        "skill is not an Ultimate action for Ultimate damage evaluation",
    )
    assert delegate.calls == []


def test_ultimate_adapter_rejects_delegate_evidence_for_different_schedule_entry() -> None:
    ultimate = RotationAction(
        1.0,
        2,
        RotationActionKind.ULTIMATE,
        name="meteor",
        bar="front",
    )
    service = RotationCandidateUltimateDamageEvidenceService(
        skill_damage_delegate=_MismatchedDelegate(),
    )

    with pytest.raises(ValueError, match="different scheduled action"):
        service.evaluate_action(candidate=_candidate(ultimate), action=ultimate)
