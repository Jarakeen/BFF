from minmax.skill_component_trigger_relationship import (
    SkillComponentTriggerType,
    extract_explicit_component_trigger_relationships,
)


def test_delayed_component_uses_delay_elapsed_trigger():
    rows = extract_explicit_component_trigger_relationships(
        skill_rank_id=6341,
        coefficient_number=2,
        component_text="After 10 seconds the webs explode, dealing $2 Poison Damage to enemies within.",
    )
    assert len(rows) == 1
    assert rows[0].trigger_type is SkillComponentTriggerType.DELAY_ELAPSED
    assert rows[0].trigger_count is None


def test_spell_orb_preserves_charge_threshold_count():
    rows = extract_explicit_component_trigger_relationships(
        skill_rank_id=7173,
        coefficient_number=1,
        component_text=(
            "When you reach 5 spell charges, you launch a spell orb at the closest enemy "
            "to you dealing $1 Magic Damage."
        ),
    )
    assert len(rows) == 1
    assert rows[0].trigger_type is SkillComponentTriggerType.CHARGE_THRESHOLD_REACHED
    assert rows[0].trigger_count == 5


def test_burning_light_preserves_stack_threshold_count():
    rows = extract_explicit_component_trigger_relationships(
        skill_rank_id=5773,
        coefficient_number=1,
        component_text="After reaching 4 stacks, you deal $1 Magic Damage to your target.",
    )
    assert len(rows) == 1
    assert rows[0].trigger_type is SkillComponentTriggerType.STACK_THRESHOLD_REACHED
    assert rows[0].trigger_count == 4


def test_static_reverberation_uses_damage_dealt_trigger():
    rows = extract_explicit_component_trigger_relationships(
        skill_rank_id=7779,
        coefficient_number=1,
        component_text=(
            "When you deal damage, you have a 5% chance to deal $1 Shock Damage, "
            "up to once every 0.3 seconds."
        ),
    )
    assert len(rows) == 1
    assert rows[0].trigger_type is SkillComponentTriggerType.DAMAGE_DEALT
    assert rows[0].trigger_count is None


def test_crystal_fragments_uses_non_ultimate_ability_cast_trigger():
    rows = extract_explicit_component_trigger_relationships(
        skill_rank_id=6394,
        coefficient_number=2,
        component_text=(
            "While slotted on either bar, casting a non-Ultimate ability has a 33% chance "
            "of causing your next Crystal Fragments to be instant cast at half cost, "
            "dealing $2 Magic Damage."
        ),
    )
    assert len(rows) == 1
    assert rows[0].trigger_type is SkillComponentTriggerType.NON_ULTIMATE_ABILITY_CAST


def test_flame_lash_uses_ability_reactivation_trigger_for_heal_component():
    rows = extract_explicit_component_trigger_relationships(
        skill_rank_id=4778,
        coefficient_number=4,
        component_text=(
            "Activating again consumes a stack to deal $3 Flame Damage to your target "
            "and all nearby enemies and heals for $4 Health."
        ),
    )
    assert len(rows) == 1
    assert rows[0].trigger_type is SkillComponentTriggerType.ABILITY_REACTIVATED


def test_generic_damage_wording_does_not_become_damage_dealt_trigger():
    rows = extract_explicit_component_trigger_relationships(
        skill_rank_id=1,
        coefficient_number=1,
        component_text="Deal $1 Flame Damage to an enemy.",
    )
    assert rows == ()


def test_generic_cast_wording_does_not_become_non_ultimate_cast_trigger():
    rows = extract_explicit_component_trigger_relationships(
        skill_rank_id=1,
        coefficient_number=1,
        component_text="Cast the ability to deal $1 Magic Damage.",
    )
    assert rows == ()


def test_generic_after_word_without_duration_does_not_become_delay_trigger():
    rows = extract_explicit_component_trigger_relationships(
        skill_rank_id=1,
        coefficient_number=1,
        component_text="After blocking, deal $1 Physical Damage.",
    )
    assert rows == ()
