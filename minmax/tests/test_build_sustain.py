from minmax.ability_cost_repository import AbilityCostResolution
from minmax.base_character_state import BaseCharacterState
from minmax.build_action_cost_modifiers import BuildActionCostModifiers
from minmax.build_calculation_context import BuildCalculationContext
from minmax.build_sustain import (
    NamedBuildAction,
    PlannedBuildAction,
    evaluate_build_sustain,
    resolve_named_build_actions,
)
from minmax.character_progression import CharacterProgression
from minmax.resource_cost_modifiers import (
    ActionCostModifier,
    ActionCostModifierSet,
    CostModifierOperation,
)
from minmax.resource_costs import ResourceType, resolve_base_action_cost
from minmax.restoration_events import ResourceRestorationEvent
from models.build_model import PlayerBuild


class _FakeCostModifierResolver:
    def __init__(self, result: BuildActionCostModifiers):
        self.result = result
        self.calls = []

    def resolve(self, build, *, progression=None):
        self.calls.append((build, progression))
        return self.result


class _FakeAbilityCostRepository:
    def __init__(self):
        self.calls = []

    def resolve_name(self, name: str) -> AbilityCostResolution:
        self.calls.append(name)
        if name == "Missing Skill":
            return AbilityCostResolution(
                None,
                name,
                None,
                ("ability cost row not found",),
            )
        return AbilityCostResolution(
            _magicka_cost(),
            "Combat Prayer",
            "Restoration Staff",
            ("No coefficient rows found for resolved skill rank",),
        )


def _context(*, max_magicka: int = 10000, magicka_recovery: int = 1000) -> BuildCalculationContext:
    return BuildCalculationContext(
        character_id="character-1",
        build_id="build-1",
        progression=CharacterProgression(owned_skill_lines=("Restoration Staff",)),
        character_state=BaseCharacterState(
            max_health=20000,
            max_magicka=max_magicka,
            max_stamina=9000,
            health_recovery=300,
            magicka_recovery=magicka_recovery,
            stamina_recovery=700,
            traces={},
        ),
    )


def _magicka_cost(amount: int = 2000):
    return resolve_base_action_cost(
        ability_id=12345,
        base_cost=amount,
        base_mechanic=1,
        rank=4,
        morph=1,
    )


def test_resolve_named_build_actions_preserves_cost_evidence_once() -> None:
    repository = _FakeAbilityCostRepository()

    resolution = resolve_named_build_actions(
        (
            NamedBuildAction(1.0, "Combat Prayer"),
            NamedBuildAction(2.0, "Missing Skill"),
        ),
        ability_cost_repository=repository,
    )

    assert repository.calls == ["Combat Prayer", "Missing Skill"]
    assert len(resolution.actions) == 1
    assert resolution.actions[0].time_seconds == 1.0
    assert resolution.actions[0].source == "Combat Prayer"
    assert resolution.actions[0].skill_line == "Restoration Staff"
    assert resolution.actions[0].base_cost.amount == 2000
    assert resolution.unresolved == ("Missing Skill: ability cost row not found",)


def test_resolve_named_build_actions_reuses_same_plan_per_repository() -> None:
    repository = _FakeAbilityCostRepository()
    actions = (
        NamedBuildAction(1.0, "Combat Prayer"),
        NamedBuildAction(2.0, "Missing Skill"),
    )

    first = resolve_named_build_actions(actions, ability_cost_repository=repository)
    second = resolve_named_build_actions(actions, ability_cost_repository=repository)

    assert first is second
    assert repository.calls == ["Combat Prayer", "Missing Skill"]


def test_resolve_named_build_actions_invalidates_for_changed_plan_or_repository() -> None:
    repository = _FakeAbilityCostRepository()
    original = (NamedBuildAction(1.0, "Combat Prayer"),)
    changed = (NamedBuildAction(2.0, "Combat Prayer"),)

    first = resolve_named_build_actions(original, ability_cost_repository=repository)
    second = resolve_named_build_actions(changed, ability_cost_repository=repository)
    fresh_repository = _FakeAbilityCostRepository()
    third = resolve_named_build_actions(original, ability_cost_repository=fresh_repository)

    assert first is not second
    assert first is not third
    assert repository.calls == ["Combat Prayer", "Combat Prayer"]
    assert fresh_repository.calls == ["Combat Prayer"]


def test_reused_action_plan_keeps_candidate_pool_and_recovery_specific() -> None:
    repository = _FakeAbilityCostRepository()
    actions = (
        NamedBuildAction(1.0, "Combat Prayer"),
        NamedBuildAction(3.0, "Combat Prayer"),
    )
    resolution = resolve_named_build_actions(actions, ability_cost_repository=repository)
    resolver = _FakeCostModifierResolver(BuildActionCostModifiers())
    build = PlayerBuild(Name="Test Healer", BuildName="Sustain")

    baseline = evaluate_build_sustain(
        build=build,
        context=_context(max_magicka=5000, magicka_recovery=500),
        resource=ResourceType.MAGICKA,
        duration_seconds=4.0,
        actions=resolution.actions,
        cost_modifier_resolver=resolver,
        additional_unresolved=resolution.unresolved,
    )
    candidate = evaluate_build_sustain(
        build=build,
        context=_context(max_magicka=9000, magicka_recovery=1500),
        resource=ResourceType.MAGICKA,
        duration_seconds=4.0,
        actions=resolution.actions,
        cost_modifier_resolver=resolver,
        additional_unresolved=resolution.unresolved,
    )

    assert repository.calls == ["Combat Prayer", "Combat Prayer"]
    assert baseline.timeline.starting_amount == 5000
    assert candidate.timeline.starting_amount == 9000
    assert [tick.amount for tick in baseline.recovery_ticks] == [500, 500]
    assert [tick.amount for tick in candidate.recovery_ticks] == [1500, 1500]
    assert baseline.timeline.ending_amount != candidate.timeline.ending_amount


def test_saved_build_sustain_uses_context_pool_build_modifiers_and_recovery() -> None:
    build = PlayerBuild(Name="Test Healer", BuildName="Sustain")
    resolver = _FakeCostModifierResolver(
        BuildActionCostModifiers(
            modifiers=ActionCostModifierSet(
                (
                    ActionCostModifier(
                        source="Verified build reduction",
                        operation=CostModifierOperation.PERCENT_REDUCTION,
                        value=0.10,
                        resources=(ResourceType.MAGICKA,),
                    ),
                )
            )
        )
    )

    run = evaluate_build_sustain(
        build=build,
        context=_context(),
        resource=ResourceType.MAGICKA,
        duration_seconds=4.0,
        actions=(
            PlannedBuildAction(1.0, "Skill A", _magicka_cost(), "Restoration Staff"),
            PlannedBuildAction(3.0, "Skill B", _magicka_cost(), "Restoration Staff"),
        ),
        cost_modifier_resolver=resolver,
    )

    assert [event.amount for event in run.action_cost_events] == [1800, 1800]
    assert [event.time_seconds for event in run.recovery_ticks] == [2.0, 4.0]
    assert run.timeline.starting_amount == 10000
    assert run.timeline.ending_amount == 8400
    assert run.sustain.sustains
    assert run.sustain.total_cost_attempted == 3600
    assert run.sustain.total_restoration_applied == 2000
    assert resolver.calls == [(build, _context().progression)]


def test_saved_build_sustain_applies_explicit_restoration_events_and_clamps() -> None:
    resolver = _FakeCostModifierResolver(BuildActionCostModifiers())

    run = evaluate_build_sustain(
        build=PlayerBuild(),
        context=_context(),
        resource=ResourceType.MAGICKA,
        duration_seconds=2.0,
        actions=(PlannedBuildAction(1.0, "Skill", _magicka_cost(4000)),),
        cost_modifier_resolver=resolver,
        restoration_events=(
            ResourceRestorationEvent(1.5, ResourceType.MAGICKA, 5000, "Heavy attack"),
            ResourceRestorationEvent(1.5, ResourceType.STAMINA, 5000, "Wrong resource"),
        ),
    )

    assert len(run.restoration_events) == 1
    assert run.restoration_events[0].source == "Heavy attack"
    assert run.timeline.ending_amount == 10000
    assert run.sustain.total_restoration_wasted == 2000


def test_saved_build_sustain_preserves_unresolved_build_cost_mechanics() -> None:
    resolver = _FakeCostModifierResolver(
        BuildActionCostModifiers(unresolved=("Evocation not verified for 3 Light pieces",))
    )

    run = evaluate_build_sustain(
        build=PlayerBuild(),
        context=_context(),
        resource=ResourceType.MAGICKA,
        duration_seconds=1.0,
        actions=(),
        cost_modifier_resolver=resolver,
    )

    assert run.unresolved == ("Evocation not verified for 3 Light pieces",)


def test_saved_build_sustain_filters_actions_after_window_and_rejects_ultimate_pool() -> None:
    resolver = _FakeCostModifierResolver(BuildActionCostModifiers())
    run = evaluate_build_sustain(
        build=PlayerBuild(),
        context=_context(),
        resource=ResourceType.MAGICKA,
        duration_seconds=2.0,
        actions=(PlannedBuildAction(3.0, "Too late", _magicka_cost()),),
        cost_modifier_resolver=resolver,
    )
    assert run.action_cost_events == ()

    try:
        evaluate_build_sustain(
            build=PlayerBuild(),
            context=_context(),
            resource=ResourceType.ULTIMATE,
            duration_seconds=2.0,
            actions=(),
            cost_modifier_resolver=resolver,
        )
    except ValueError as exc:
        assert "primary resource pools only" in str(exc)
    else:
        raise AssertionError("Expected Ultimate sustain pool to be rejected")
