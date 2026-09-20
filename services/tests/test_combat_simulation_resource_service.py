from __future__ import annotations

from types import SimpleNamespace

from minmax.resource_costs import ResourceType
from minmax.resource_timeline import (
    AppliedResourceTimelineEvent,
    ResourceTimelineEventKind,
    ResourceTimelineResult,
)
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from models.build_model import PlayerBuild
from models.combat_simulation import SimulationEventPriority
from models.effective_build_snapshot import EffectiveBuildSnapshot
from services.combat_simulation_resource_service import CombatSimulationResourceService
from services.combat_simulation_service import CombatSimulationService


class _FakeSustainService:
    def evaluate(self, *, build, plan, resource):
        assert build.Name == "Magrat"
        assert plan.build_name == "DF Healer"
        assert resource is ResourceType.MAGICKA
        timeline = ResourceTimelineResult(
            resource=ResourceType.MAGICKA,
            starting_amount=30000,
            ending_amount=26600,
            events=(
                AppliedResourceTimelineEvent(
                    time_seconds=0.0,
                    kind=ResourceTimelineEventKind.ACTION_COST,
                    source="Combat Prayer",
                    before=30000,
                    attempted_change=-3000,
                    applied_change=-3000,
                    after=27000,
                ),
                AppliedResourceTimelineEvent(
                    time_seconds=2.0,
                    kind=ResourceTimelineEventKind.RECOVERY_TICK,
                    source="In-combat recovery tick",
                    before=27000,
                    attempted_change=1600,
                    applied_change=1600,
                    after=28600,
                ),
                AppliedResourceTimelineEvent(
                    time_seconds=2.0,
                    kind=ResourceTimelineEventKind.ACTION_COST,
                    source="Illustrious Healing",
                    before=28600,
                    attempted_change=-2000,
                    applied_change=-2000,
                    after=26600,
                ),
            ),
            starting_maximum=30000,
            ending_maximum=30000,
        )
        return SimpleNamespace(
            run=SimpleNamespace(timeline=timeline),
            unresolved=(),
        )


def _plan() -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=4.0,
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
            EsoClass="Warden",
            Role="Healer",
        )
    )


def test_resource_adapter_preserves_phase4_before_after_and_shortfall_evidence() -> None:
    projection = CombatSimulationResourceService(
        sustain_service=_FakeSustainService()
    ).project(
        build=_snapshot().materialize(),
        plan=_plan(),
        resource=ResourceType.MAGICKA,
    )

    assert projection.result.resource == "magicka"
    assert projection.result.starting_amount == 30000
    assert projection.result.ending_amount == 26600
    assert projection.result.total_shortfall == 0

    first = projection.events[0]
    assert first.event_type == "action_cost"
    assert first.source == "Combat Prayer"
    assert first.priority == int(SimulationEventPriority.RESOURCE_COST)
    assert first.payload_dict()["before"] == 30000
    assert first.payload_dict()["after"] == 27000
    assert first.payload_dict()["applied_change"] == -3000

    recovery = projection.events[1]
    assert recovery.event_type == "recovery_tick"
    assert recovery.priority == int(SimulationEventPriority.RESOURCE_RESTORE)
    assert recovery.payload_dict()["after"] == 28600


def test_simulation_merges_healer_actions_and_resource_events_deterministically() -> None:
    service = CombatSimulationService(
        resource_service=CombatSimulationResourceService(
            sustain_service=_FakeSustainService()
        )
    )

    first = service.simulate(build_snapshot=_snapshot(), plan=_plan())
    second = service.simulate(build_snapshot=_snapshot(), plan=_plan())

    assert first == second
    assert first.resources[0].starting_amount == 30000
    assert first.resources[0].ending_amount == 26600

    at_zero = [
        (event.priority, event.event_type, event.source)
        for event in first.events
        if event.time_seconds == 0.0
    ]
    assert at_zero == [
        (int(SimulationEventPriority.ACTION), "action", "Combat Prayer"),
        (int(SimulationEventPriority.RESOURCE_COST), "action_cost", "Combat Prayer"),
    ]

    at_two = [
        (event.priority, event.event_type, event.source)
        for event in first.events
        if event.time_seconds == 2.0
    ]
    assert at_two == [
        (int(SimulationEventPriority.ACTION), "action", "bar_swap"),
        (int(SimulationEventPriority.ACTION), "action", "Illustrious Healing"),
        (int(SimulationEventPriority.RESOURCE_COST), "action_cost", "Illustrious Healing"),
        (int(SimulationEventPriority.RESOURCE_RESTORE), "recovery_tick", "In-combat recovery tick"),
    ]

    assert not any(
        "Combat Prayer" in value and "consequence projection not yet wired" in value
        for value in first.unresolved
    )
    assert not any(
        "Illustrious Healing" in value and "consequence projection not yet wired" in value
        for value in first.unresolved
    )
