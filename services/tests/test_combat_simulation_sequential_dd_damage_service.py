from __future__ import annotations

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from models.combat_simulation import (
    CombatSimulationCombatant,
    CombatSimulationTargetState,
)
from services.combat_simulation_sequential_dd_damage_service import (
    CombatSimulationSequentialDDDamageService,
    CombatSimulationTargetHealthLedger,
)
from services.rotation_candidate_dd_role_output_service import RotationActionDamageEvidence
from services.rotation_candidate_generation_service import GeneratedRotationCandidate


class _ThresholdAwareProvider:
    def __init__(self, snapshot_resolver):
        self.snapshot_resolver = snapshot_resolver
        self.seen_health = []

    def evaluate_action(self, *, candidate, action):
        del candidate
        snapshot = self.snapshot_resolver(action.time_seconds, action.sequence)
        target = snapshot.target("Boss")
        health = target.current_health
        maximum = target.maximum_health
        self.seen_health.append((action.sequence, health, maximum))
        damage = 7000.0 if (health / maximum) < 0.5 else 6000.0
        return RotationActionDamageEvidence(
            time_seconds=action.time_seconds,
            sequence=action.sequence,
            damage_value=damage,
        )


def _plan():
    return RotationPlan(
        character_name="Damage Tester",
        build_name="DD Build",
        duration_seconds=5.0,
        actions=(
            RotationAction(
                time_seconds=1.0,
                sequence=0,
                kind=RotationActionKind.SKILL,
                name="Opening Hit",
                bar="front",
            ),
            RotationAction(
                time_seconds=2.0,
                sequence=0,
                kind=RotationActionKind.SKILL,
                name="Execute Hit",
                bar="front",
            ),
        ),
    )


def _state():
    return CombatSimulationTargetState(
        combatants=(
            CombatSimulationCombatant(
                "Boss",
                "enemy",
                current_health=10000,
                maximum_health=10000,
            ),
        ),
    )


def test_sequential_damage_updates_health_before_next_action_evaluation() -> None:
    plan = _plan()
    candidate = GeneratedRotationCandidate(
        candidate_id="sequential-health",
        plan=plan,
        refresh_leads=(),
        action_claims=(),
    )
    ledger = CombatSimulationTargetHealthLedger(
        target_state=_state(),
        target_identity="Boss",
        player_identity="Damage Tester",
    )
    provider = _ThresholdAwareProvider(ledger.snapshot_at)

    result = CombatSimulationSequentialDDDamageService().project(
        plan=plan,
        candidate=candidate,
        action_damage_evidence_provider=provider,
        target_state=_state(),
        target_identity="Boss",
        player_identity="Damage Tester",
        ledger=ledger,
    )

    assert provider.seen_health == [
        (0, 10000.0, 10000.0),
        (0, 4000.0, 10000.0),
    ]
    assert [item.amount for item in result.damage] == [6000.0, 7000.0]
    assert ledger.current_health == 0.0
    assert result.unresolved == ()


def test_sequential_damage_preserves_same_timestamp_sequence_health_order() -> None:
    plan = RotationPlan(
        character_name="Damage Tester",
        build_name="DD Build",
        duration_seconds=2.0,
        actions=(
            RotationAction(
                time_seconds=1.0,
                sequence=0,
                kind=RotationActionKind.SKILL,
                name="First",
                bar="front",
            ),
            RotationAction(
                time_seconds=1.0,
                sequence=1,
                kind=RotationActionKind.SKILL,
                name="Second",
                bar="front",
            ),
        ),
    )
    candidate = GeneratedRotationCandidate(
        candidate_id="same-time-sequence",
        plan=plan,
        refresh_leads=(),
        action_claims=(),
    )
    ledger = CombatSimulationTargetHealthLedger(
        target_state=_state(),
        target_identity="Boss",
        player_identity="Damage Tester",
    )
    provider = _ThresholdAwareProvider(ledger.snapshot_at)

    CombatSimulationSequentialDDDamageService().project(
        plan=plan,
        candidate=candidate,
        action_damage_evidence_provider=provider,
        target_state=_state(),
        target_identity="Boss",
        player_identity="Damage Tester",
        ledger=ledger,
    )

    assert provider.seen_health == [
        (0, 10000.0, 10000.0),
        (1, 4000.0, 10000.0),
    ]


def test_health_ledger_requires_explicit_target_health() -> None:
    state = CombatSimulationTargetState(
        combatants=(CombatSimulationCombatant("Boss", "enemy"),),
    )

    try:
        CombatSimulationTargetHealthLedger(
            target_state=state,
            target_identity="Boss",
            player_identity="Damage Tester",
        )
    except ValueError as exc:
        assert "current and maximum Health" in str(exc)
    else:
        raise AssertionError("Expected missing target Health to fail closed")
