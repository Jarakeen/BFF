from __future__ import annotations

from minmax.ability_cost_repository import AbilityCostResolution
from minmax.base_character_state import BaseCharacterState
from minmax.build_action_cost_modifiers import BuildActionCostModifiers
from minmax.build_calculation_context import BuildCalculationContext
from minmax.build_sustain import NamedBuildAction, evaluate_named_build_sustain
from minmax.character_progression import CharacterProgression
from minmax.resource_costs import ResourceType, resolve_base_action_cost
from models.build_model import PlayerBuild


class _FakeAbilityCostRepository:
    def __init__(self, resolutions):
        self.resolutions = resolutions
        self.calls = []

    def resolve_name(self, name):
        self.calls.append(name)
        return self.resolutions[name]


class _FakeCostModifierResolver:
    def resolve(self, build, *, progression=None):
        return BuildActionCostModifiers()


def _context() -> BuildCalculationContext:
    return BuildCalculationContext(
        character_id="character-1",
        build_id="build-1",
        progression=CharacterProgression(owned_skill_lines=("Restoration Staff",)),
        character_state=BaseCharacterState(
            max_health=20000,
            max_magicka=10000,
            max_stamina=9000,
            health_recovery=300,
            magicka_recovery=1000,
            stamina_recovery=700,
            traces={},
        ),
    )


def _cost(amount=3000):
    return resolve_base_action_cost(
        ability_id=41151,
        base_cost=amount,
        base_mechanic=1,
        rank=4,
        morph=1,
    )


def test_named_build_sustain_resolves_skill_name_into_timeline_cost() -> None:
    ability_repository = _FakeAbilityCostRepository(
        {
            "Combat Prayer": AbilityCostResolution(
                base_cost=_cost(),
                name="Combat Prayer",
                skill_line="Restoration Staff",
            )
        }
    )

    run = evaluate_named_build_sustain(
        build=PlayerBuild(Name="Healer"),
        context=_context(),
        resource=ResourceType.MAGICKA,
        duration_seconds=2.0,
        actions=(NamedBuildAction(1.0, "Combat Prayer"),),
        ability_cost_repository=ability_repository,
        cost_modifier_resolver=_FakeCostModifierResolver(),
    )

    assert ability_repository.calls == ["Combat Prayer"]
    assert len(run.action_cost_events) == 1
    assert run.action_cost_events[0].source == "Combat Prayer"
    assert run.action_cost_events[0].amount == 3000
    assert run.timeline.ending_amount == 8000
    assert run.unresolved == ()


def test_named_build_sustain_preserves_unresolved_skill_and_does_not_charge_it() -> None:
    ability_repository = _FakeAbilityCostRepository(
        {
            "Mystery Skill": AbilityCostResolution(
                base_cost=None,
                name="Mystery Skill",
                skill_line=None,
                unresolved=("Skill name not found: Mystery Skill",),
            )
        }
    )

    run = evaluate_named_build_sustain(
        build=PlayerBuild(),
        context=_context(),
        resource=ResourceType.MAGICKA,
        duration_seconds=1.0,
        actions=(NamedBuildAction(0.5, "Mystery Skill"),),
        ability_cost_repository=ability_repository,
        cost_modifier_resolver=_FakeCostModifierResolver(),
    )

    assert run.action_cost_events == ()
    assert run.unresolved == ("Mystery Skill: Skill name not found: Mystery Skill",)


def test_named_build_sustain_ignores_coefficient_warning_for_valid_resource_cost() -> None:
    ability_repository = _FakeAbilityCostRepository(
        {
            "Utility Skill": AbilityCostResolution(
                base_cost=_cost(2000),
                name="Utility Skill",
                skill_line="Restoration Staff",
                unresolved=("No coefficient rows found for utility_skill (source ability 41151)",),
            )
        }
    )

    run = evaluate_named_build_sustain(
        build=PlayerBuild(),
        context=_context(),
        resource=ResourceType.MAGICKA,
        duration_seconds=1.0,
        actions=(NamedBuildAction(0.5, "Utility Skill"),),
        ability_cost_repository=ability_repository,
        cost_modifier_resolver=_FakeCostModifierResolver(),
    )

    assert len(run.action_cost_events) == 1
    assert run.unresolved == ()
