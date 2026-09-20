from __future__ import annotations

from types import SimpleNamespace

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from models.build_model import PlayerBuild
from models.combat_simulation import SimulationEventPriority
from models.effective_build_snapshot import EffectiveBuildSnapshot
from services.combat_simulation_healing_service import (
    CombatSimulationHealingProjection,
    CombatSimulationHealingService,
)
from services.combat_simulation_resource_service import CombatSimulationResourceProjection
from models.combat_simulation import CombatSimulationResourceResult
from services.combat_simulation_service import CombatSimulationService
from services.rotation_healer_action_healing_service import (
    RotationHealerActionHealingProjection,
    RotationHealerPeriodicHealSeed,
    RotationHealerResolvedHealEvent,
)


class _StaticContexts:
    resolved = True
    unresolved = ()
    contexts = (
        SimpleNamespace(active_bar="front"),
        SimpleNamespace(active_bar="back"),
    )

    def context_for(self, bar):
        for item in self.contexts:
            if item.active_bar == bar:
                return item
        return None


class _StaticContextService:
    def resolve(self, build):
        assert build.Name == "Magrat"
        return _StaticContexts()


class _ActionHealingService:
    def project(self, *, plan, build, context, contexts_by_bar):
        assert plan.build_name == "DF Healer"
        assert build.Role == "Healer"
        assert context.active_bar == "front"
        assert set(contexts_by_bar) == {"front", "back"}
        return RotationHealerActionHealingProjection(
            direct_events=(
                RotationHealerResolvedHealEvent(
                    time_seconds=0.0,
                    sequence=0,
                    source_name="Combat Prayer",
                    coefficient_number=1,
                    modeled_heal=8123.5,
                ),
            ),
            periodic_seeds=(
                RotationHealerPeriodicHealSeed(
                    time_seconds=2.0,
                    sequence=1,
                    source_name="Illustrious Healing",
                    coefficient_number=1,
                    modeled_heal=1456.25,
                ),
            ),
            unresolved=(),
        )


class _NoopResourceService:
    def project(self, **_kwargs):
        return CombatSimulationResourceProjection(
            result=CombatSimulationResourceResult(
                resource="magicka",
                starting_amount=30000,
                ending_amount=30000,
                total_shortfall=0,
            ),
            events=(),
            unresolved=(),
        )


def _plan() -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=5.0,
        actions=(
            RotationAction(
                0.0,
                0,
                RotationActionKind.SKILL,
                name="Combat Prayer",
                bar="front",
            ),
            RotationAction(
                2.0,
                0,
                RotationActionKind.BAR_SWAP,
                bar="back",
            ),
            RotationAction(
                2.0,
                1,
                RotationActionKind.SKILL,
                name="Illustrious Healing",
                bar="back",
            ),
        ),
    )


def _snapshot() -> EffectiveBuildSnapshot:
    return EffectiveBuildSnapshot.from_saved_build(
        PlayerBuild(
            Name="Magrat",
            BuildName="DF Healer",
            Role="Healer",
            EsoClass="Warden",
        )
    )


def _healing_service() -> CombatSimulationHealingService:
    return CombatSimulationHealingService(
        action_healing_service=_ActionHealingService(),
        static_context_service=_StaticContextService(),
    )


def test_healer_output_bridge_emits_direct_heal_and_periodic_seed() -> None:
    result = _healing_service().project(
        build=_snapshot().materialize(),
        plan=_plan(),
    )

    assert [(event.event_type, event.source) for event in result.events] == [
        ("direct_heal", "Combat Prayer"),
        ("periodic_heal_seed", "Illustrious Healing"),
    ]

    direct = result.events[0]
    assert direct.priority == int(SimulationEventPriority.DIRECT_RESULT)
    assert direct.payload_dict()["coefficient_number"] == 1
    assert direct.payload_dict()["modeled_heal"] == 8123.5

    seed = result.events[1]
    assert seed.priority == int(SimulationEventPriority.TRIGGER)
    assert seed.payload_dict()["modeled_heal"] == 1456.25
    assert any(
        "Illustrious Healing coefficient 1" in message
        and "exact tick events require reviewed runtime timing evidence" in message
        for message in result.unresolved
    )


def test_simulation_merges_healing_output_deterministically() -> None:
    service = CombatSimulationService(
        resource_service=_NoopResourceService(),
        healing_service=_healing_service(),
    )

    first = service.simulate(build_snapshot=_snapshot(), plan=_plan())
    second = service.simulate(build_snapshot=_snapshot(), plan=_plan())

    assert first == second

    at_zero = [
        (event.priority, event.event_type, event.source)
        for event in first.events
        if event.time_seconds == 0.0
    ]
    assert at_zero == [
        (int(SimulationEventPriority.ACTION), "action", "Combat Prayer"),
        (int(SimulationEventPriority.DIRECT_RESULT), "direct_heal", "Combat Prayer"),
    ]

    at_two = [
        (event.priority, event.event_type, event.source)
        for event in first.events
        if event.time_seconds == 2.0
    ]
    assert at_two == [
        (int(SimulationEventPriority.ACTION), "action", "bar_swap"),
        (int(SimulationEventPriority.ACTION), "action", "Illustrious Healing"),
        (int(SimulationEventPriority.TRIGGER), "periodic_heal_seed", "Illustrious Healing"),
    ]

    assert any(
        "Combat Prayer" in message and "damage/effects" in message
        for message in first.unresolved
    )
    assert any(
        "Illustrious Healing coefficient 1" in message
        and "reviewed runtime timing evidence" in message
        for message in first.unresolved
    )


def test_healer_output_bridge_fails_closed_without_static_context() -> None:
    class _UnresolvedStatic:
        def resolve(self, _build):
            return SimpleNamespace(
                resolved=False,
                unresolved=("front static context unresolved",),
                contexts=(),
                context_for=lambda _bar: None,
            )

    result = CombatSimulationHealingService(
        action_healing_service=_ActionHealingService(),
        static_context_service=_UnresolvedStatic(),
    ).project(
        build=_snapshot().materialize(),
        plan=_plan(),
    )

    assert result.events == ()
    assert result.unresolved == ("front static context unresolved",)
