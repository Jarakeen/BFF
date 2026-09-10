import pytest

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_candidate_dd_role_output_service import (
    RotationActionDamageEvidence,
    RotationCandidateDDRoleOutputService,
)
from services.rotation_candidate_generation_service import GeneratedRotationCandidate


def _candidate(*actions: RotationAction, duration_seconds: float = 10.0) -> GeneratedRotationCandidate:
    return GeneratedRotationCandidate(
        candidate_id="candidate",
        plan=RotationPlan(
            character_name="Damage Tester",
            build_name="DD Build",
            duration_seconds=duration_seconds,
            actions=tuple(actions),
        ),
        refresh_leads=(),
        action_claims=(),
    )


class _DamageProvider:
    def __init__(self, by_key):
        self.by_key = dict(by_key)
        self.calls = []

    def evaluate_action(self, *, candidate, action):
        self.calls.append((candidate, action))
        return self.by_key[(action.time_seconds, action.sequence)]


def test_dd_role_output_aggregates_resolved_damage_actions_into_effective_dps() -> None:
    skill = RotationAction(0.0, 0, RotationActionKind.SKILL, name="deep_fissure", bar="front")
    light = RotationAction(0.0, 1, RotationActionKind.LIGHT_ATTACK, bar="front")
    ultimate = RotationAction(5.0, 0, RotationActionKind.ULTIMATE, name="wild_guardian", bar="front")
    swap = RotationAction(6.0, 0, RotationActionKind.BAR_SWAP, bar="back")
    wait = RotationAction(7.0, 0, RotationActionKind.WAIT)
    candidate = _candidate(skill, light, ultimate, swap, wait, duration_seconds=10.0)
    provider = _DamageProvider(
        {
            (0.0, 0): RotationActionDamageEvidence(0.0, 0, 1000.0),
            (0.0, 1): RotationActionDamageEvidence(0.0, 1, 250.0),
            (5.0, 0): RotationActionDamageEvidence(5.0, 0, 2750.0),
        }
    )
    service = RotationCandidateDDRoleOutputService(
        action_damage_evidence_provider=provider,
    )

    evidence = service.evaluate_plan(candidate)

    assert evidence.candidate_id == "candidate"
    assert evidence.value == 400.0
    assert evidence.unresolved == ()
    assert [call[1] for call in provider.calls] == [skill, light, ultimate]


def test_dd_role_output_fails_closed_when_any_required_damage_action_is_unresolved() -> None:
    skill = RotationAction(0.0, 0, RotationActionKind.SKILL, name="skill_x", bar="front")
    light = RotationAction(0.0, 1, RotationActionKind.LIGHT_ATTACK, bar="front")
    candidate = _candidate(skill, light)
    provider = _DamageProvider(
        {
            (0.0, 0): RotationActionDamageEvidence(0.0, 0, 1000.0),
            (0.0, 1): RotationActionDamageEvidence(
                0.0,
                1,
                None,
                unresolved=("light-attack combat consequence unresolved",),
            ),
        }
    )
    service = RotationCandidateDDRoleOutputService(
        action_damage_evidence_provider=provider,
    )

    evidence = service.evaluate_plan(candidate)

    assert evidence.value is None
    assert evidence.unresolved == ("light-attack combat consequence unresolved",)


def test_dd_role_output_does_not_treat_missing_damage_value_as_zero() -> None:
    skill = RotationAction(2.0, 0, RotationActionKind.SKILL, name="skill_x", bar="front")
    candidate = _candidate(skill)
    provider = _DamageProvider(
        {(2.0, 0): RotationActionDamageEvidence(2.0, 0, None)}
    )
    service = RotationCandidateDDRoleOutputService(
        action_damage_evidence_provider=provider,
    )

    evidence = service.evaluate_plan(candidate)

    assert evidence.value is None
    assert evidence.unresolved == (
        "2s #0 skill: damage consequence unavailable",
    )


def test_dd_role_output_rejects_damage_evidence_for_a_different_scheduled_action() -> None:
    skill = RotationAction(2.0, 0, RotationActionKind.SKILL, name="skill_x", bar="front")
    candidate = _candidate(skill)
    provider = _DamageProvider(
        {(2.0, 0): RotationActionDamageEvidence(3.0, 0, 1000.0)}
    )
    service = RotationCandidateDDRoleOutputService(
        action_damage_evidence_provider=provider,
    )

    with pytest.raises(ValueError, match="damage evidence mismatch"):
        service.evaluate_plan(candidate)


def test_dd_role_output_requires_positive_plan_duration() -> None:
    candidate = _candidate(duration_seconds=0.0)
    service = RotationCandidateDDRoleOutputService(
        action_damage_evidence_provider=_DamageProvider({}),
    )

    evidence = service.evaluate_plan(candidate)

    assert evidence.value is None
    assert evidence.unresolved == (
        "whole-plan DD output requires positive rotation duration",
    )


def test_action_damage_evidence_rejects_invalid_damage_values() -> None:
    with pytest.raises(ValueError, match="finite and non-negative"):
        RotationActionDamageEvidence(0.0, 0, -1.0)

    with pytest.raises(ValueError, match="finite and non-negative"):
        RotationActionDamageEvidence(0.0, 0, float("nan"))
