from minmax.skill_component_resource_restore_display import (
    SkillComponentRestoreDisplayBasis,
    SkillComponentRestoreDisplayDriver,
    SkillComponentRestoreDisplayResource,
    extract_explicit_component_resource_restore_display,
)


def test_undaunted_current_health_restore_display():
    rows = extract_explicit_component_resource_restore_display(
        skill_rank_id=6568,
        coefficient_number=1,
        component_text=(
            "Activating a synergy restores 2% of your Max Health, Stamina, and Magicka. "
            "Current Bonus: $1 Health, $2 Stamina, and $3 Magicka."
        ),
    )
    assert len(rows) == 1
    row = rows[0]
    assert row.resources == (SkillComponentRestoreDisplayResource.HEALTH,)
    assert row.basis is SkillComponentRestoreDisplayBasis.PERCENT_MAX_RESOURCE
    assert row.amount_fraction == 0.02


def test_undaunted_current_stamina_restore_display():
    rows = extract_explicit_component_resource_restore_display(
        skill_rank_id=6569,
        coefficient_number=2,
        component_text=(
            "Activating a synergy restores 4% of your Max Health, Stamina, and Magicka. "
            "Current Bonus: $1 Health, $2 Stamina, and $3 Magicka."
        ),
    )
    assert rows[0].resources == (SkillComponentRestoreDisplayResource.STAMINA,)
    assert rows[0].amount_fraction == 0.04


def test_constitution_current_bonus_is_flat_per_heavy_piece_for_both_resources():
    rows = extract_explicit_component_resource_restore_display(
        skill_rank_id=5636,
        coefficient_number=2,
        component_text=(
            "Increases your Health Recovery by 2% for each piece of Heavy Armor equipped. "
            "Current bonus: $1%. You restore 108 Magicka and Stamina when you take damage "
            "for each piece of Heavy Armor equipped. This effect can occur once every 8 seconds. "
            "Current bonus: $2."
        ),
    )
    assert len(rows) == 1
    row = rows[0]
    assert row.resources == (
        SkillComponentRestoreDisplayResource.MAGICKA,
        SkillComponentRestoreDisplayResource.STAMINA,
    )
    assert row.basis is SkillComponentRestoreDisplayBasis.FLAT_PER_UNIT
    assert row.amount_per_unit == 108.0
    assert row.driver is SkillComponentRestoreDisplayDriver.HEAVY_ARMOR_PIECES_EQUIPPED


def test_bare_current_bonus_is_not_promoted():
    assert extract_explicit_component_resource_restore_display(
        skill_rank_id=1,
        coefficient_number=1,
        component_text="Current bonus: $1.",
    ) == ()
