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
from services.rotation_candidate_dd_role_output_service import (
    RotationActionDamageEvidence,
    RotationActionDamageOccurrence,
    RotationActionDamageOccurrenceEvidence,
)
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



class _RecordingFixedProvider:
    def __init__(self, damage):
        self.damage = float(damage)
        self.calls = []

    def evaluate_action(self, *, candidate, action):
        del candidate
        self.calls.append((action.time_seconds, action.sequence, action.name))
        return RotationActionDamageEvidence(
            time_seconds=action.time_seconds,
            sequence=action.sequence,
            damage_value=self.damage,
        )


def test_sequential_damage_stops_evaluating_after_target_death() -> None:
    plan = RotationPlan(
        character_name="Damage Tester",
        build_name="DD Build",
        duration_seconds=5.0,
        actions=(
            RotationAction(
                time_seconds=1.0,
                sequence=0,
                kind=RotationActionKind.SKILL,
                name="Killing Hit",
                bar="front",
            ),
            RotationAction(
                time_seconds=2.0,
                sequence=0,
                kind=RotationActionKind.SKILL,
                name="Post Death Hit",
                bar="front",
            ),
        ),
    )
    candidate = GeneratedRotationCandidate(
        candidate_id="death-stop",
        plan=plan,
        refresh_leads=(),
        action_claims=(),
    )
    ledger = CombatSimulationTargetHealthLedger(
        target_state=_state(),
        target_identity="Boss",
        player_identity="Damage Tester",
    )
    provider = _RecordingFixedProvider(12000.0)

    result = CombatSimulationSequentialDDDamageService().project(
        plan=plan,
        candidate=candidate,
        action_damage_evidence_provider=provider,
        target_state=_state(),
        target_identity="Boss",
        player_identity="Damage Tester",
        ledger=ledger,
    )

    assert provider.calls == [(1.0, 0, "Killing Hit")]
    assert [item.source for item in result.damage] == ["Killing Hit"]
    assert result.terminated_at_seconds == 1.0
    assert result.terminated_at_sequence == 0
    assert result.suppressed_action_keys == ((2.0, 0),)

    replay = result.evidence_provider()
    post = plan.actions[1]
    evidence = replay.evaluate_action(candidate=candidate, action=post)
    assert evidence.damage_value == 0.0
    assert evidence.unresolved == ()



class _OccurrenceProvider:
    def __init__(self):
        self.calls = []

    def evaluate_action_occurrences(self, *, candidate, action):
        del candidate
        self.calls.append((action.time_seconds, action.sequence, action.name))
        if action.name == "DoT":
            return RotationActionDamageOccurrenceEvidence(
                action_time_seconds=action.time_seconds,
                action_sequence=action.sequence,
                occurrences=(
                    RotationActionDamageOccurrence(
                        time_seconds=action.time_seconds,
                        sequence=action.sequence,
                        damage_value=1000.0,
                        source_name="DoT",
                        coefficient_number=1,
                    ),
                    RotationActionDamageOccurrence(
                        time_seconds=1.0,
                        sequence=0,
                        damage_value=2000.0,
                        source_name="DoT",
                        coefficient_number=2,
                        occurrence_index=0,
                    ),
                ),
            )
        return RotationActionDamageOccurrenceEvidence(
            action_time_seconds=action.time_seconds,
            action_sequence=action.sequence,
            occurrences=(
                RotationActionDamageOccurrence(
                    time_seconds=action.time_seconds,
                    sequence=action.sequence,
                    damage_value=3000.0,
                    source_name=str(action.name),
                    coefficient_number=1,
                ),
            ),
        )


def test_sequential_damage_applies_periodic_occurrences_at_tick_times() -> None:
    plan = RotationPlan(
        character_name="Damage Tester",
        build_name="DD Build",
        duration_seconds=3.0,
        actions=(
            RotationAction(
                time_seconds=0.0,
                sequence=0,
                kind=RotationActionKind.SKILL,
                name="DoT",
                bar="front",
            ),
            RotationAction(
                time_seconds=2.0,
                sequence=0,
                kind=RotationActionKind.SKILL,
                name="Direct",
                bar="front",
            ),
        ),
    )
    candidate = GeneratedRotationCandidate(
        candidate_id="periodic-occurrences",
        plan=plan,
        refresh_leads=(),
        action_claims=(),
    )
    provider = _OccurrenceProvider()

    result = CombatSimulationSequentialDDDamageService().project(
        plan=plan,
        candidate=candidate,
        action_damage_evidence_provider=provider,
        target_state=_state(),
        target_identity="Boss",
        player_identity="Damage Tester",
    )

    assert [
        (item.time_seconds, item.source, item.amount)
        for item in result.damage
    ] == [
        (0.0, "DoT", 1000.0),
        (1.0, "DoT", 2000.0),
        (2.0, "Direct", 3000.0),
    ]
    assert result.terminated_at_seconds is None
    assert result.unresolved == ()


class _HealthAwareOccurrenceProvider:
    def __init__(self, snapshot_resolver):
        self.snapshot_resolver = snapshot_resolver
        self.seen = []

    def evaluate_action_occurrences(self, *, candidate, action):
        del candidate
        snapshot = self.snapshot_resolver(action.time_seconds, action.sequence)
        target = snapshot.target("Boss")
        self.seen.append((action.name, target.current_health))
        if action.name == "DoT":
            return RotationActionDamageOccurrenceEvidence(
                action_time_seconds=action.time_seconds,
                action_sequence=action.sequence,
                occurrences=(
                    RotationActionDamageOccurrence(
                        time_seconds=1.0,
                        sequence=0,
                        damage_value=6000.0,
                        source_name="DoT",
                        coefficient_number=1,
                        occurrence_index=0,
                    ),
                ),
            )
        return RotationActionDamageOccurrenceEvidence(
            action_time_seconds=action.time_seconds,
            action_sequence=action.sequence,
            occurrences=(
                RotationActionDamageOccurrence(
                    time_seconds=action.time_seconds,
                    sequence=action.sequence,
                    damage_value=7000.0 if target.current_health < 5000 else 1000.0,
                    source_name=str(action.name),
                    coefficient_number=1,
                ),
            ),
        )


def test_periodic_tick_health_feeds_later_action_evaluation() -> None:
    plan = RotationPlan(
        character_name="Damage Tester",
        build_name="DD Build",
        duration_seconds=3.0,
        actions=(
            RotationAction(
                time_seconds=0.0,
                sequence=0,
                kind=RotationActionKind.SKILL,
                name="DoT",
                bar="front",
            ),
            RotationAction(
                time_seconds=2.0,
                sequence=0,
                kind=RotationActionKind.SKILL,
                name="Execute",
                bar="front",
            ),
        ),
    )
    candidate = GeneratedRotationCandidate(
        candidate_id="dot-execute",
        plan=plan,
        refresh_leads=(),
        action_claims=(),
    )
    ledger = CombatSimulationTargetHealthLedger(
        target_state=_state(),
        target_identity="Boss",
        player_identity="Damage Tester",
    )
    provider = _HealthAwareOccurrenceProvider(ledger.snapshot_at)

    result = CombatSimulationSequentialDDDamageService().project(
        plan=plan,
        candidate=candidate,
        action_damage_evidence_provider=provider,
        target_state=_state(),
        target_identity="Boss",
        player_identity="Damage Tester",
        ledger=ledger,
    )

    assert provider.seen == [
        ("DoT", 10000.0),
        ("Execute", 4000.0),
    ]
    assert [(item.time_seconds, item.amount) for item in result.damage] == [
        (1.0, 6000.0),
        (2.0, 7000.0),
    ]
    assert result.terminated_at_seconds == 2.0
