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
from services.rotation_candidate_dd_role_output_service import RotationActionDamageEvidence


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
