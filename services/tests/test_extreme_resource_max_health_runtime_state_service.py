from types import SimpleNamespace

import pytest

from minmax.character_build.character_class import CharacterClass
from models.build_model import PlayerBuild
from services.class_mastery_repository import ClassMasteryPassive
from services.extreme_resource_max_health_runtime_state_service import (
    ExtremeResourceMaxHealthRuntimeStateService,
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


def _route(*, base_class, lines, mastery_allowed, subclassed=False):
    return SimpleNamespace(
        base_class=base_class,
        equipped_skill_lines=tuple(lines),
        class_mastery_allowed=mastery_allowed,
        is_subclassed=subclassed,
    )


def test_daedric_summoning_and_green_balance_stack_reviewed_health_witnesses():
    service = ExtremeResourceMaxHealthRuntimeStateService(
        mastery_repository=_MasteryRepository()
    )
    route = _route(
        base_class=CharacterClass.TEMPLAR,
        lines=("restoring_light", "daedric_summoning", "green_balance"),
        mastery_allowed=False,
        subclassed=True,
    )

    catalog = service.build(route)

    assert catalog.denominator_proven is True
    assert catalog.unresolved == ()
    state = catalog.states[0]
    assert state.permanent_pet_active is True
    assert state.maturation_minor_toughness_active is True
    assert state.reviewed_percent_bonus == pytest.approx(0.15)
    assert state.nothing_wasted_stacks == 0
    assert state.class_mastery_ability_ids == ()
    assert "Maturation" in state.label
    assert any("Green Balance" in condition for condition in state.conditions)


def test_green_balance_route_selects_maturation_minor_toughness_witness():
    service = ExtremeResourceMaxHealthRuntimeStateService(
        mastery_repository=_MasteryRepository()
    )
    route = _route(
        base_class=CharacterClass.WARDEN,
        lines=("animal_companions", "green_balance", "winters_embrace"),
        mastery_allowed=True,
    )

    catalog = service.build(route)

    assert catalog.denominator_proven is True
    assert catalog.unresolved == ()
    state = catalog.states[0]
    assert state.permanent_pet_active is False
    assert state.maturation_minor_toughness_active is True
    assert state.reviewed_percent_bonus == pytest.approx(0.10)
    assert state.label == "Maturation Minor Toughness"


def test_pure_necromancer_selects_nothing_wasted_ten_stack_witness():
    service = ExtremeResourceMaxHealthRuntimeStateService(
        mastery_repository=_MasteryRepository()
    )
    route = _route(
        base_class=CharacterClass.NECROMANCER,
        lines=("grave_lord", "bone_tyrant", "living_death"),
        mastery_allowed=True,
    )

    catalog = service.build(route)

    assert catalog.denominator_proven is True
    state = catalog.states[0]
    assert state.permanent_pet_active is False
    assert state.maturation_minor_toughness_active is False
    assert state.nothing_wasted_stacks == 10
    assert state.class_mastery_ability_ids == (987654,)
    assert state.reviewed_percent_bonus == 0.20
    build = service.materialize(PlayerBuild(EsoClass="Necromancer"), state)
    assert build.ClassMasteryAbilityIds == [987654]


def test_route_without_reviewed_health_runtime_effect_keeps_zero_witness():
    service = ExtremeResourceMaxHealthRuntimeStateService(
        mastery_repository=_MasteryRepository()
    )
    route = _route(
        base_class=CharacterClass.TEMPLAR,
        lines=("aedric_spear", "dawns_wrath", "restoring_light"),
        mastery_allowed=True,
    )

    catalog = service.build(route)

    assert catalog.denominator_proven is True
    state = catalog.states[0]
    assert state.reviewed_percent_bonus == 0.0
    assert state.permanent_pet_active is False
    assert state.maturation_minor_toughness_active is False
    assert state.nothing_wasted_stacks == 0


def test_missing_nothing_wasted_identity_fails_closed():
    class _EmptyRepository:
        @staticmethod
        def for_class(_class_name):
            return ()

    service = ExtremeResourceMaxHealthRuntimeStateService(
        mastery_repository=_EmptyRepository()
    )
    route = _route(
        base_class=CharacterClass.NECROMANCER,
        lines=("grave_lord", "bone_tyrant", "living_death"),
        mastery_allowed=True,
    )

    catalog = service.build(route)

    assert catalog.denominator_proven is False
    assert catalog.unresolved
    assert catalog.states[0].reviewed_percent_bonus == 0.0
