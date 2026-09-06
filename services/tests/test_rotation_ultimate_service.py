from types import SimpleNamespace

from models.build_model import PlayerBuild
from minmax.resource_costs import BaseActionCost, ResourceType
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.ultimate_resource_timeline import UltimateGenerationEvent
from services.rotation_ultimate_service import RotationUltimateService


class _FakeCostRepository:
    def __init__(self, resolution):
        self.resolution = resolution
        self.calls = []

    def resolve_name(self, name):
        self.calls.append(name)
        return self.resolution


def _build() -> PlayerBuild:
    build = PlayerBuild(Name="Magrat", BuildName="DF Healer")
    build.FrontBarSkills = ["Skill", "", "", "", "", "Aggressive Horn"]
    build.BackBarSkills = ["", "", "", "", "", "Barrier"]
    return build


def _plan() -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=4.0,
        actions=(
            RotationAction(0.0, 0, RotationActionKind.SKILL, "Skill", "front"),
            RotationAction(1.0, 0, RotationActionKind.SKILL, "Skill", "front"),
            RotationAction(2.0, 0, RotationActionKind.BAR_SWAP, bar="back"),
            RotationAction(3.0, 0, RotationActionKind.SKILL, "Back Skill", "back"),
            RotationAction(4.0, 0, RotationActionKind.SKILL, "Back Skill", "back"),
        ),
    )


def _long_plan() -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=12.0,
        actions=tuple(
            RotationAction(float(second), 0, RotationActionKind.SKILL, "Skill", "front")
            for second in range(13)
        ),
    )


def _resolution(name="Aggressive Horn", resource=ResourceType.ULTIMATE):
    return SimpleNamespace(
        name=name,
        base_cost=BaseActionCost(
            amount=250.0,
            resources=(resource,),
            ability_id=1,
            rank=4,
            morph=1,
            base_mechanic=8 if resource is ResourceType.ULTIMATE else 1,
        ),
        unresolved=(),
    )


def test_service_resolves_saved_slot_six_ultimate_and_schedules_explicit_availability() -> None:
    repository = _FakeCostRepository(_resolution())
    service = RotationUltimateService(ability_cost_repository=repository)

    result = service.apply(
        build=_build(),
        plan=_plan(),
        availability_by_bar={"front": (1.0,)},
    )

    assert repository.calls == ["Aggressive Horn"]
    assert len(result.rules) == 1
    assert result.rules[0].cost == 250.0
    cast = next(action for action in result.plan.actions if action.kind is RotationActionKind.ULTIMATE)
    assert cast.time_seconds == 1.0
    assert cast.name == "Aggressive Horn"


def test_service_does_not_schedule_without_explicit_availability() -> None:
    repository = _FakeCostRepository(_resolution())
    service = RotationUltimateService(ability_cost_repository=repository)

    result = service.apply(build=_build(), plan=_plan())

    assert repository.calls == []
    assert result.rules == ()
    assert not any(action.kind is RotationActionKind.ULTIMATE for action in result.plan.actions)
    assert any("no explicit Ultimate availability evidence" in item for item in result.unresolved)


def test_service_rejects_slot_six_ability_without_ultimate_resource_mechanic() -> None:
    repository = _FakeCostRepository(_resolution(resource=ResourceType.MAGICKA))
    service = RotationUltimateService(ability_cost_repository=repository)

    result = service.apply(
        build=_build(),
        plan=_plan(),
        availability_by_bar={"front": (1.0,)},
    )

    assert result.rules == ()
    assert not any(action.kind is RotationActionKind.ULTIMATE for action in result.plan.actions)
    assert any("without the Ultimate resource mechanic" in item for item in result.unresolved)


def test_service_keeps_front_and_back_ultimate_availability_separate() -> None:
    class PerNameRepository:
        def __init__(self):
            self.calls = []

        def resolve_name(self, name):
            self.calls.append(name)
            return _resolution(name=name)

    repository = PerNameRepository()
    service = RotationUltimateService(ability_cost_repository=repository)

    result = service.apply(
        build=_build(),
        plan=_plan(),
        availability_by_bar={"back": (3.0,)},
    )

    assert repository.calls == ["Barrier"]
    assert len(result.rules) == 1
    assert result.rules[0].bar == "back"
    cast = next(action for action in result.plan.actions if action.kind is RotationActionKind.ULTIMATE)
    assert cast.time_seconds == 3.0
    assert cast.bar == "back"
    assert cast.name == "Barrier"


def test_generation_bridge_derives_affordability_and_schedules_ultimate() -> None:
    repository = _FakeCostRepository(_resolution())
    service = RotationUltimateService(ability_cost_repository=repository)

    result = service.apply_generation(
        build=_build(),
        plan=_long_plan(),
        starting_ultimate_by_bar={"front": 100.0},
        generation_events_by_bar={
            "front": (
                UltimateGenerationEvent(5.0, 75.0, "explicit gain A"),
                UltimateGenerationEvent(10.0, 75.0, "explicit gain B"),
            )
        },
    )

    assert repository.calls == ["Aggressive Horn", "Barrier"]
    assert len(result.resource_projections) == 2
    front_projection = dict(result.resource_projections)["front"]
    assert front_projection.availability_times == (10.0,)
    horn = next(
        action
        for action in result.plan.actions
        if action.kind is RotationActionKind.ULTIMATE
        and action.name == "Aggressive Horn"
    )
    assert horn.time_seconds == 10.0
    assert horn.bar == "front"


def test_generation_bridge_keeps_unaffordable_ultimate_unscheduled() -> None:
    repository = _FakeCostRepository(_resolution())
    service = RotationUltimateService(ability_cost_repository=repository)

    result = service.apply_generation(
        build=_build(),
        plan=_long_plan(),
        starting_ultimate_by_bar={"front": 100.0},
        generation_events_by_bar={
            "front": (UltimateGenerationEvent(5.0, 100.0, "explicit gain"),)
        },
    )

    assert not any(
        action.kind is RotationActionKind.ULTIMATE
        and action.name == "Aggressive Horn"
        for action in result.plan.actions
    )
    assert any("never became affordable" in item for item in result.unresolved)
