import pytest

from minmax.formulas.status_effects import (
    calculate_magical_ability_status_chance,
    calculate_magical_aoe_dot_status_chance,
    calculate_magical_aoe_status_chance,
    calculate_magical_dot_status_chance,
    calculate_magical_enchant_status_chance,
    calculate_martial_ability_status_chance,
    calculate_martial_aoe_dot_status_chance,
    calculate_martial_aoe_status_chance,
    calculate_martial_dot_status_chance,
    calculate_martial_enchant_status_chance,
    calculate_poisoned_duration,
    calculate_status_duration,
)


def test_calculate_poisoned_duration():
    assert calculate_poisoned_duration() == 6.0


def test_calculate_status_duration():
    assert calculate_status_duration() == 4.0
    assert calculate_status_duration(
        set_status_effect_duration=2.0,
    ) == 6.0


@pytest.mark.parametrize(
    ("calculator", "expected"),
    [
        (calculate_magical_enchant_status_chance, 0.20),
        (calculate_magical_ability_status_chance, 0.10),
        (calculate_magical_aoe_status_chance, 0.05),
        (calculate_magical_dot_status_chance, 0.03),
        (calculate_magical_aoe_dot_status_chance, 0.01),
    ],
)
def test_magical_status_chances_without_modifiers(calculator, expected):
    assert calculator() == pytest.approx(expected)


@pytest.mark.parametrize(
    ("calculator", "expected"),
    [
        (calculate_martial_enchant_status_chance, 0.20),
        (calculate_martial_ability_status_chance, 0.10),
        (calculate_martial_aoe_status_chance, 0.05),
        (calculate_martial_dot_status_chance, 0.03),
        (calculate_martial_aoe_dot_status_chance, 0.01),
    ],
)
def test_martial_status_chances_without_modifiers(calculator, expected):
    assert calculator() == pytest.approx(expected)


def test_magical_enchant_status_chance_with_modifiers():
    assert calculate_magical_enchant_status_chance(
        skill_status_effect_chance=0.10,
        set_status_effect_chance=0.05,
        item_status_effect_chance=0.02,
        cp_magical_status_effect_chance=0.03,
    ) == pytest.approx(0.20 * 1.20)


def test_magical_ability_status_chance_with_modifiers():
    assert calculate_magical_ability_status_chance(
        skill_status_effect_chance=0.10,
        set_status_effect_chance=0.05,
        item_status_effect_chance=0.02,
        cp_magical_status_effect_chance=0.03,
    ) == pytest.approx(0.10 * 1.20)


def test_martial_enchant_status_chance_with_modifiers():
    assert calculate_martial_enchant_status_chance(
        skill_status_effect_chance=0.10,
        set_status_effect_chance=0.05,
        item_status_effect_chance=0.02,
        cp_martial_status_effect_chance=0.03,
    ) == pytest.approx(0.20 * 1.20)


def test_magical_and_martial_use_their_own_cp_modifier():
    magical = calculate_magical_enchant_status_chance(
        cp_magical_status_effect_chance=0.10,
    )

    martial = calculate_martial_enchant_status_chance(
        cp_martial_status_effect_chance=0.50,
    )

    assert magical == pytest.approx(0.20 * 1.10)
    assert martial == pytest.approx(0.20 * 1.50)


def test_all_status_chance_inputs_can_be_zero():
    assert calculate_magical_enchant_status_chance() == pytest.approx(0.20)
    assert calculate_martial_enchant_status_chance() == pytest.approx(0.20)