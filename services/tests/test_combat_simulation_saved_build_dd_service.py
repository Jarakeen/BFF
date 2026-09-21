from __future__ import annotations

from dataclasses import dataclass

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from models.build_model import PlayerBuild
from models.combat_simulation import (
    CombatSimulationCombatant,
    CombatSimulationResourceResult,
    CombatSimulationTargetState,
)
from models.effective_build_snapshot import EffectiveBuildSnapshot
from services.combat_simulation_healing_service import CombatSimulationHealingProjection
from services.combat_simulation_resource_service import CombatSimulationResourceProjection
from services.combat_simulation_saved_build_dd_provider_service import (
    CombatSimulationSavedBuildDDProviderResolution,
)
from services.combat_simulation_saved_build_dd_service import (
    CombatSimulationSavedBuildDDService,
)
from services.combat_simulation_service import CombatSimulationService
from services.combat_simulation_skill_effect_service import CombatSimulationEffectProjection
from services.rotation_candidate_dd_role_output_service import (
    RotationActionDamageEvidence,
    RotationActionDamageOccurrence,
    RotationActionDamageOccurrenceEvidence,
)


class _NoopResourceService:
    def project(self, **_kwargs):
        return CombatSimulationResourceProjection(
            result=CombatSimulationResourceResult(
                resource="magicka",
                starting_amount=0,
                ending_amount=0,
                total_shortfall=0,
            ),
            events=(),
            unresolved=(),
        )


class _NoopHealingService:
    def project(self, **_kwargs):
        return CombatSimulationHealingProjection(events=(), unresolved=())


class _NoopSkillEffectService:
    def project(self, **_kwargs):
        return CombatSimulationEffectProjection(events=(), windows=(), unresolved=())


class _Provider:
    def evaluate_action(self, *, candidate, action):
        del candidate
        if action.kind is RotationActionKind.SKILL:
            return RotationActionDamageEvidence(
                time_seconds=action.time_seconds,
                sequence=action.sequence,
                damage_value=4000.0,
            )
        return RotationActionDamageEvidence(
            time_seconds=action.time_seconds,
            sequence=action.sequence,
            damage_value=None,
            unresolved=("unsupported fixture action",),
        )


class _ProviderService:
    def __init__(self, *, unresolved=()):
        self.unresolved = tuple(unresolved)
        self.calls = []

    def resolve(self, **kwargs):
        self.calls.append(kwargs)
        return CombatSimulationSavedBuildDDProviderResolution(
            provider=_Provider() if not self.unresolved else None,
            unresolved=self.unresolved,
        )


def _snapshot():
    return EffectiveBuildSnapshot.from_saved_build(
        PlayerBuild(
            Name="Damage Tester",
            BuildName="DD Build",
            Role="DD",
            EsoClass="Nightblade",
        ),
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
                name="Impale",
                bar="front",
            ),
        ),
    )


def _simulation_service():
    return CombatSimulationService(
        resource_service=_NoopResourceService(),
        healing_service=_NoopHealingService(),
        skill_effect_service=_NoopSkillEffectService(),
    )


def test_saved_build_dd_orchestrator_applies_provider_damage_to_enemy_health() -> None:
    provider_service = _ProviderService()
    service = CombatSimulationSavedBuildDDService(
        provider_service=provider_service,
        simulation_service=_simulation_service(),
    )
    state = CombatSimulationTargetState(
        combatants=(
            CombatSimulationCombatant(
                "Boss",
                "enemy",
                current_health=10000,
                maximum_health=10000,
            ),
        ),
    )

    result = service.simulate(
        build_snapshot=_snapshot(),
        plan=_plan(),
        target_state=state,
        damage_target_identity="Boss",
        target_resistance=18200.0,
    )

    outgoing = [event for event in result.events if event.event_type == "outgoing_damage"]
    health = [event for event in result.events if event.event_type == "health_change"]

    assert len(provider_service.calls) == 1
    assert provider_service.calls[0]["target_resistance"] == 18200.0
    assert outgoing[0].source == "Impale"
    assert outgoing[0].payload_dict()["amount"] == 4000.0
    assert health[0].payload_dict()["before"] == 10000
    assert health[0].payload_dict()["after"] == 6000
    assert any(
        "damage consequence is wired" in message
        for message in result.unresolved
    )


def test_saved_build_dd_orchestrator_preserves_provider_resolution_failure() -> None:
    service = CombatSimulationSavedBuildDDService(
        provider_service=_ProviderService(
            unresolved=("canonical DD static build evidence is unresolved",)
        ),
        simulation_service=_simulation_service(),
    )
    state = CombatSimulationTargetState(
        combatants=(
            CombatSimulationCombatant(
                "Boss",
                "enemy",
                current_health=10000,
                maximum_health=10000,
            ),
        ),
    )

    result = service.simulate(
        build_snapshot=_snapshot(),
        plan=_plan(),
        target_state=state,
        damage_target_identity="Boss",
        target_resistance=18200.0,
    )

    assert not any(event.event_type == "outgoing_damage" for event in result.events)
    assert "canonical DD static build evidence is unresolved" in result.unresolved
    assert any(
        "remaining skill consequences" in message
        for message in result.unresolved
    )



class _ThresholdProvider:
    def __init__(self, snapshot_resolver):
        self.snapshot_resolver = snapshot_resolver
        self.seen = []

    def evaluate_action(self, *, candidate, action):
        del candidate
        snapshot = self.snapshot_resolver(action.time_seconds, action.sequence)
        target = snapshot.target("Boss")
        fraction = target.current_health / target.maximum_health
        self.seen.append((action.name, target.current_health, fraction))
        return RotationActionDamageEvidence(
            time_seconds=action.time_seconds,
            sequence=action.sequence,
            damage_value=(7000.0 if fraction < 0.5 else 6000.0),
        )


class _ThresholdProviderService:
    def __init__(self):
        self.provider = None

    def resolve(self, **kwargs):
        self.provider = _ThresholdProvider(kwargs["target_snapshot_resolver"])
        return CombatSimulationSavedBuildDDProviderResolution(
            provider=self.provider,
            unresolved=(),
        )


def test_saved_build_dd_orchestrator_feeds_simulated_health_into_later_damage() -> None:
    provider_service = _ThresholdProviderService()
    service = CombatSimulationSavedBuildDDService(
        provider_service=provider_service,
        simulation_service=_simulation_service(),
    )
    plan = RotationPlan(
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
    state = CombatSimulationTargetState(
        combatants=(
            CombatSimulationCombatant(
                "Boss",
                "enemy",
                current_health=10000,
                maximum_health=10000,
            ),
        ),
    )

    result = service.simulate(
        build_snapshot=_snapshot(),
        plan=plan,
        target_state=state,
        damage_target_identity="Boss",
        target_resistance=18200.0,
    )

    assert provider_service.provider is not None
    assert provider_service.provider.seen == [
        ("Opening Hit", 10000.0, 1.0),
        ("Execute Hit", 4000.0, 0.4),
    ]
    outgoing = [
        event.payload_dict()["amount"]
        for event in result.events
        if event.event_type == "outgoing_damage"
    ]
    assert outgoing == [6000.0, 7000.0]
    health = [
        event.payload_dict()["after"]
        for event in result.events
        if event.event_type == "health_change"
        and event.payload_dict().get("recipient") == "Boss"
    ]
    assert health == [4000, 0]
    assert result.duration_seconds == 2.0
    assert not any(
        event.time_seconds > 2.0
        for event in result.events
    )



class _PeriodicOccurrenceProvider:
    def evaluate_action_occurrences(self, *, candidate, action):
        del candidate
        return RotationActionDamageOccurrenceEvidence(
            action_time_seconds=action.time_seconds,
            action_sequence=action.sequence,
            occurrences=(
                RotationActionDamageOccurrence(
                    time_seconds=action.time_seconds,
                    sequence=action.sequence,
                    damage_value=1000.0,
                    source_name=str(action.name),
                    coefficient_number=1,
                ),
                RotationActionDamageOccurrence(
                    time_seconds=action.time_seconds + 1.0,
                    sequence=0,
                    damage_value=2000.0,
                    source_name=str(action.name),
                    coefficient_number=2,
                    occurrence_index=0,
                ),
            ),
        )


class _PeriodicOccurrenceProviderService:
    def resolve(self, **_kwargs):
        return CombatSimulationSavedBuildDDProviderResolution(
            provider=_PeriodicOccurrenceProvider(),
            unresolved=(),
        )


def test_saved_build_dd_orchestrator_replays_periodic_occurrence_timestamps() -> None:
    service = CombatSimulationSavedBuildDDService(
        provider_service=_PeriodicOccurrenceProviderService(),
        simulation_service=_simulation_service(),
    )
    plan = RotationPlan(
        character_name="Damage Tester",
        build_name="DD Build",
        duration_seconds=4.0,
        actions=(
            RotationAction(
                time_seconds=0.0,
                sequence=0,
                kind=RotationActionKind.SKILL,
                name="Mixed Skill",
                bar="front",
            ),
        ),
    )
    state = CombatSimulationTargetState(
        combatants=(
            CombatSimulationCombatant(
                "Boss",
                "enemy",
                current_health=10000,
                maximum_health=10000,
            ),
        ),
    )

    result = service.simulate(
        build_snapshot=_snapshot(),
        plan=plan,
        target_state=state,
        damage_target_identity="Boss",
        target_resistance=18200.0,
    )

    outgoing = [
        (event.time_seconds, event.source, event.payload_dict()["amount"])
        for event in result.events
        if event.event_type == "outgoing_damage"
    ]
    health = [
        (event.time_seconds, event.payload_dict()["after"])
        for event in result.events
        if event.event_type == "health_change"
        and event.payload_dict().get("recipient") == "Boss"
    ]

    assert outgoing == [
        (0.0, "Mixed Skill", 1000.0),
        (1.0, "Mixed Skill", 2000.0),
    ]
    assert health == [(0.0, 9000), (1.0, 7000)]



class _LethalPeriodicOccurrenceProvider:
    def evaluate_action_occurrences(self, *, candidate, action):
        del candidate
        if action.name == "DoT":
            return RotationActionDamageOccurrenceEvidence(
                action_time_seconds=action.time_seconds,
                action_sequence=action.sequence,
                occurrences=(
                    RotationActionDamageOccurrence(
                        time_seconds=1.0,
                        sequence=0,
                        damage_value=12000.0,
                        source_name="DoT",
                        coefficient_number=1,
                        occurrence_index=0,
                    ),
                ),
            )
        raise AssertionError("post-death action should never be evaluated")


class _LethalPeriodicProviderService:
    def resolve(self, **_kwargs):
        return CombatSimulationSavedBuildDDProviderResolution(
            provider=_LethalPeriodicOccurrenceProvider(),
            unresolved=(),
        )


def test_periodic_tick_can_terminate_saved_build_simulation() -> None:
    service = CombatSimulationSavedBuildDDService(
        provider_service=_LethalPeriodicProviderService(),
        simulation_service=_simulation_service(),
    )
    plan = RotationPlan(
        character_name="Damage Tester",
        build_name="DD Build",
        duration_seconds=5.0,
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
                name="Too Late",
                bar="front",
            ),
        ),
    )
    state = CombatSimulationTargetState(
        combatants=(
            CombatSimulationCombatant(
                "Boss",
                "enemy",
                current_health=10000,
                maximum_health=10000,
            ),
        ),
    )

    result = service.simulate(
        build_snapshot=_snapshot(),
        plan=plan,
        target_state=state,
        damage_target_identity="Boss",
        target_resistance=18200.0,
    )

    assert result.duration_seconds == 1.0
    outgoing = [
        event
        for event in result.events
        if event.event_type == "outgoing_damage"
    ]
    deaths = [
        event
        for event in result.events
        if event.event_type == "death"
    ]
    assert [(event.time_seconds, event.source) for event in outgoing] == [
        (1.0, "DoT"),
    ]
    assert [(event.time_seconds, event.source) for event in deaths] == [
        (1.0, "DoT"),
    ]
    assert not any(event.time_seconds > 1.0 for event in result.events)


class _LethalSameTimestampProvider:
    def evaluate_action(self, *, candidate, action):
        del candidate
        if action.name == "Killing Hit":
            return RotationActionDamageEvidence(
                time_seconds=action.time_seconds,
                sequence=action.sequence,
                damage_value=12000.0,
            )
        raise AssertionError("later same-timestamp action should not execute after death")


class _LethalSameTimestampProviderService:
    def resolve(self, **_kwargs):
        return CombatSimulationSavedBuildDDProviderResolution(
            provider=_LethalSameTimestampProvider(),
            unresolved=(),
        )


def test_same_timestamp_later_sequence_is_excluded_after_lethal_action() -> None:
    service = CombatSimulationSavedBuildDDService(
        provider_service=_LethalSameTimestampProviderService(),
        simulation_service=_simulation_service(),
    )
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
                time_seconds=1.0,
                sequence=1,
                kind=RotationActionKind.SKILL,
                name="Too Late Same Timestamp",
                bar="front",
            ),
        ),
    )
    state = CombatSimulationTargetState(
        combatants=(
            CombatSimulationCombatant(
                "Boss",
                "enemy",
                current_health=10000,
                maximum_health=10000,
            ),
        ),
    )

    result = service.simulate(
        build_snapshot=_snapshot(),
        plan=plan,
        target_state=state,
        damage_target_identity="Boss",
        target_resistance=18200.0,
    )

    actions = [
        (event.time_seconds, event.sequence, event.source)
        for event in result.events
        if event.event_type == "action"
    ]
    assert actions == [(1.0, 0, "Killing Hit")]
    assert result.duration_seconds == 1.0
    assert not any(
        event.time_seconds == 1.0 and event.sequence > 0
        for event in result.events
    )
