import pytest

from minmax.character_progression import CharacterProgression
from minmax.context_factory import BuildCalculationContextFactory
from models.build_model import PlayerBuild
from services.class_mastery_repository import ClassMasteryPassive
from services.extreme_resource_max_health_runtime_context_service import (
    ExtremeResourceMaxHealthRuntimeContextService,
)
from services.extreme_resource_max_health_runtime_state_service import (
    ExtremeResourceMaxHealthRuntimeState,
)


class _MasteryRepository:
    @staticmethod
    def for_class(class_name):
        if str(class_name).casefold() != "necromancer":
            return ()
        return (
            ClassMasteryPassive(
                skill_id=1,
                base_ability_id=987654,
                name="Nothing Wasted",
                class_name="Necromancer",
                description="reviewed fixture",
            ),
        )


def _service():
    return ExtremeResourceMaxHealthRuntimeContextService(
        mastery_repository=_MasteryRepository()
    )


def test_nothing_wasted_adds_twenty_percent_before_resource_rounding():
    state = ExtremeResourceMaxHealthRuntimeState(
        label="Nothing Wasted 10 stacks",
        nothing_wasted_stacks=10,
        class_mastery_ability_ids=(987654,),
        reviewed_percent_bonus=0.20,
    )
    context = _service().resolve(
        factory=BuildCalculationContextFactory(),
        build=PlayerBuild(
            EsoClass="Necromancer",
            ClassSkillLines=["grave_lord", "bone_tyrant", "living_death"],
            ClassMasteryAbilityIds=[987654],
        ),
        progression=CharacterProgression(),
        state=state,
        character_id="char",
        build_id="build",
    )

    assert context.character_state.max_health == 19200
    health_trace = context.character_state.traces[next(
        stat for stat in context.character_state.traces
        if str(stat.value) == "max_health"
    )]
    assert any(
        step.label == "Class Mastery: Nothing Wasted (10 stacks)"
        and step.operation == "percent"
        and step.value == pytest.approx(0.20)
        for step in health_trace.steps
    )


def test_maturation_routes_minor_toughness_through_canonical_named_buff_layer():
    context = _service().resolve(
        factory=BuildCalculationContextFactory(),
        build=PlayerBuild(
            EsoClass="Warden",
            ClassSkillLines=["animal_companions", "green_balance", "winters_embrace"],
        ),
        progression=CharacterProgression(
            owned_skill_lines=("green_balance",),
            passive_ranks={"Maturation": 2},
        ),
        state=ExtremeResourceMaxHealthRuntimeState(
            label="Maturation Minor Toughness",
            maturation_minor_toughness_active=True,
            reviewed_percent_bonus=0.10,
        ),
        character_id="char",
        build_id="maturation",
    )

    assert context.combat_state.has_buff("Minor Toughness") is True
    assert context.character_state.max_health == 17600


def test_zero_runtime_state_delegates_to_normal_canonical_context():
    context = _service().resolve(
        factory=BuildCalculationContextFactory(),
        build=PlayerBuild(EsoClass="Warden"),
        progression=CharacterProgression(),
        state=ExtremeResourceMaxHealthRuntimeState(
            label="No reviewed runtime Max Health bonus"
        ),
        character_id="char",
        build_id="build",
    )

    assert context.character_state.max_health == 16000


def test_partial_nothing_wasted_stack_state_fails_closed():
    state = ExtremeResourceMaxHealthRuntimeState(
        label="Nothing Wasted partial",
        nothing_wasted_stacks=5,
        class_mastery_ability_ids=(987654,),
        reviewed_percent_bonus=0.10,
    )

    with pytest.raises(ValueError, match="10-stack"):
        _service().resolve(
            factory=BuildCalculationContextFactory(),
            build=PlayerBuild(EsoClass="Necromancer"),
            progression=CharacterProgression(),
            state=state,
            character_id="char",
            build_id="build",
        )


def test_wrong_mastery_identity_fails_closed():
    state = ExtremeResourceMaxHealthRuntimeState(
        label="Nothing Wasted 10 stacks",
        nothing_wasted_stacks=10,
        class_mastery_ability_ids=(111,),
        reviewed_percent_bonus=0.20,
    )

    with pytest.raises(ValueError, match="unique canonical mastery evidence"):
        _service().resolve(
            factory=BuildCalculationContextFactory(),
            build=PlayerBuild(EsoClass="Necromancer"),
            progression=CharacterProgression(),
            state=state,
            character_id="char",
            build_id="build",
        )
