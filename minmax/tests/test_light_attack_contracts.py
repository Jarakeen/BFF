from inspect import signature

from minmax.formulas import additional_formulas, resolved_modifiers
from minmax.formulas.light_attack_contracts import LIGHT_ATTACK_CONTRACTS


def test_flame_staff_contract_matches_formula_signature():
    formula = getattr(
        resolved_modifiers,
        LIGHT_ATTACK_CONTRACTS["flame_staff"]["formula"],
    )

    expected = set(
        LIGHT_ATTACK_CONTRACTS["flame_staff"]["inputs"]
    )

    actual = set(signature(formula).parameters)

    assert actual == expected


def test_frost_staff_contract_matches_formula_signature():
    formula = getattr(
        resolved_modifiers,
        LIGHT_ATTACK_CONTRACTS["frost_staff"]["formula"],
    )

    expected = set(
        LIGHT_ATTACK_CONTRACTS["frost_staff"]["inputs"]
    )

    actual = set(signature(formula).parameters)

    assert actual == expected


def test_shock_staff_contract_matches_formula_signature():
    formula = getattr(
        resolved_modifiers,
        LIGHT_ATTACK_CONTRACTS["shock_staff"]["formula"],
    )

    expected = set(
        LIGHT_ATTACK_CONTRACTS["shock_staff"]["inputs"]
    )

    actual = set(signature(formula).parameters)

    assert actual == expected


def test_bow_contract_matches_formula_signature():
    formula = getattr(
        additional_formulas,
        LIGHT_ATTACK_CONTRACTS["bow"]["formula"],
    )

    expected = set(
        LIGHT_ATTACK_CONTRACTS["bow"]["inputs"]
    )

    actual = set(signature(formula).parameters)

    assert actual == expected


def test_base_inputs_are_not_damage_multipliers():
    flame = LIGHT_ATTACK_CONTRACTS["flame_staff"]["inputs"]

    assert flame["magicka"]["application"] == "base"
    assert flame["stamina"]["application"] == "base"
    assert flame["la_flame_spell_damage"]["application"] == "base"
    assert flame["la_flame_weapon_damage"]["application"] == "base"

    bow = LIGHT_ATTACK_CONTRACTS["bow"]["inputs"]
    assert bow["magicka"]["application"] == "base"
    assert bow["stamina"]["application"] == "base"
    assert bow["la_physical_weapon_damage"]["application"] == "base"
    assert bow["la_physical_spell_damage"]["application"] == "base"


def test_skill2_la_damage_is_base_side():
    for attack in ("flame_staff", "frost_staff", "shock_staff", "bow"):
        assert (
            LIGHT_ATTACK_CONTRACTS[attack]["inputs"]["skill2_la_damage"]["application"]
            == "additive_to_base"
        )


def test_damage_done_modifiers_are_multiplier_side():
    for attack in LIGHT_ATTACK_CONTRACTS.values():
        for name, spec in attack["inputs"].items():
            if spec["layer"] == "damage_done":
                assert spec["application"] == "multiplier"
