from minmax.combat_effect_semantics import GameUpdate
from minmax.support_target_type import SupportTargetType
from minmax.alchemy_poison_effect_semantics import (
    poison_named_effects_for_trait,
)


def test_u50_breach_poison_relationship_is_target_minor_breach() -> None:
    rows = poison_named_effects_for_trait("Breach", game_update=GameUpdate.U50)

    assert len(rows) == 1
    assert rows[0].effect_name == "Minor Breach"
    assert rows[0].target_type is SupportTargetType.ENEMY


def test_u50_protection_poison_relationship_preserves_both_sides() -> None:
    rows = poison_named_effects_for_trait(
        "Protection",
        game_update=GameUpdate.U50,
    )

    assert [
        (row.effect_name, row.target_type)
        for row in rows
    ] == [
        ("Minor Vulnerability", SupportTargetType.ENEMY),
        ("Minor Protection", SupportTargetType.SELF),
    ]


def test_relationship_lookup_is_case_and_whitespace_insensitive() -> None:
    rows = poison_named_effects_for_trait(
        "  breach ",
        game_update="U50",
    )

    assert rows[0].effect_name == "Minor Breach"


def test_u51_does_not_inherit_u50_poison_relationships() -> None:
    assert poison_named_effects_for_trait(
        "Breach",
        game_update=GameUpdate.U51,
    ) == ()


def test_unreviewed_poison_trait_remains_unmapped() -> None:
    assert poison_named_effects_for_trait(
        "Ravage Health",
        game_update=GameUpdate.U50,
    ) == ()


def test_u50_weapon_power_poison_preserves_enemy_and_self_relationships() -> None:
    rows = poison_named_effects_for_trait(
        "Increase Weapon Power",
        game_update=GameUpdate.U50,
    )

    assert [
        (row.effect_name, row.target_type)
        for row in rows
    ] == [
        ("Minor Maim", SupportTargetType.ENEMY),
        ("Minor Brutality", SupportTargetType.SELF),
    ]


def test_u50_spell_critical_poison_preserves_enemy_and_self_relationships() -> None:
    rows = poison_named_effects_for_trait(
        "Spell Critical",
        game_update=GameUpdate.U50,
    )

    assert [
        (row.effect_name, row.target_type)
        for row in rows
    ] == [
        ("Minor Uncertainty", SupportTargetType.ENEMY),
        ("Minor Prophecy", SupportTargetType.SELF),
    ]
