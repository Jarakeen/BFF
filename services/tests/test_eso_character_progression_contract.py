import pytest

from services.eso_character_progression_contract import (
    AttributeKey,
    CLASS_MASTERY_RULES,
    CRUX_RULES,
    SUBCLASSING_RULES,
    ULTIMATE_RULES,
    available_bar_count,
    base_attribute_value,
    crux_can_generate,
    ultimate_regen_from_standard_trigger,
    validate_attribute_allocation,
    validate_bar_shape,
    validate_class_mastery_eligibility,
    validate_subclass_route,
)


def test_level_50_base_attribute_formulas_match_reviewed_source_values():
    assert base_attribute_value(AttributeKey.HEALTH, level=50, attribute_points=0) == 16000.0
    assert base_attribute_value(AttributeKey.HEALTH, level=50, attribute_points=64) == 23808.0
    assert base_attribute_value(AttributeKey.MAGICKA, level=50, attribute_points=0) == 12000.0
    assert base_attribute_value(AttributeKey.MAGICKA, level=50, attribute_points=64) == 19104.0
    assert base_attribute_value(AttributeKey.STAMINA, level=50, attribute_points=64) == 19104.0


def test_attribute_allocation_cannot_exceed_64_points():
    validate_attribute_allocation(health=0, magicka=64, stamina=0)
    with pytest.raises(ValueError, match="64"):
        validate_attribute_allocation(health=10, magicka=55, stamina=0)


def test_weapon_swap_unlocks_second_bar_at_level_15():
    assert available_bar_count(14) == 1
    assert available_bar_count(15) == 2
    assert available_bar_count(50) == 2


def test_each_bar_has_five_normal_slots_and_one_ultimate_slot():
    validate_bar_shape(normal_skill_count=5, ultimate_count=1)
    with pytest.raises(ValueError, match="five"):
        validate_bar_shape(normal_skill_count=6, ultimate_count=1)
    with pytest.raises(ValueError, match="one Ultimate"):
        validate_bar_shape(normal_skill_count=5, ultimate_count=2)


def test_subclass_route_must_retain_one_native_line_and_may_take_two_foreign_lines():
    legal = validate_subclass_route(
        base_class="Warden",
        equipped_class_lines=("Green Balance", "Storm Calling", "Bone Tyrant"),
    )
    illegal = validate_subclass_route(
        base_class="Warden",
        equipped_class_lines=("Storm Calling", "Bone Tyrant", "Assassination"),
    )

    assert legal.legal is True
    assert illegal.legal is False
    assert any("retain at least one native" in error for error in illegal.errors)
    assert SUBCLASSING_RULES.maximum_foreign_class_lines_equipped == 2
    assert SUBCLASSING_RULES.class_mastery_allowed is False


def test_class_mastery_requires_three_native_lines_at_50_and_no_subclassing():
    legal = validate_class_mastery_eligibility(
        native_class_line_ranks=(50, 50, 50),
        subclassing=False,
        selected_mastery_count=2,
    )
    subclassed = validate_class_mastery_eligibility(
        native_class_line_ranks=(50, 50, 50),
        subclassing=True,
        selected_mastery_count=2,
    )
    underleveled = validate_class_mastery_eligibility(
        native_class_line_ranks=(50, 49, 50),
        subclassing=False,
        selected_mastery_count=2,
    )

    assert legal.legal is True
    assert subclassed.legal is False
    assert underleveled.legal is False
    assert CLASS_MASTERY_RULES.passives_per_class == 5
    assert CLASS_MASTERY_RULES.selectable_passives == 2


def test_standard_ultimate_regen_window_is_capped_at_27():
    assert ULTIMATE_RULES.maximum_resource == 500
    assert ultimate_regen_from_standard_trigger(3.0) == 9.0
    assert ultimate_regen_from_standard_trigger(9.0) == 27.0
    assert ultimate_regen_from_standard_trigger(99.0) == 27.0


def test_crux_generation_requires_combat_and_room_below_three_stacks():
    assert CRUX_RULES.maximum_stacks == 3
    assert CRUX_RULES.out_of_combat_expiry_seconds == 30.0
    assert crux_can_generate(in_combat=True, current_crux=2) is True
    assert crux_can_generate(in_combat=True, current_crux=3) is False
    assert crux_can_generate(in_combat=False, current_crux=0) is False
