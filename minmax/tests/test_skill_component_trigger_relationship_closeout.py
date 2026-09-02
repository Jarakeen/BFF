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


def test_generic_after_word_without_duration_does_not_become_delay_trigger():
    rows = extract_explicit_component_trigger_relationships(
        skill_rank_id=1,
        coefficient_number=1,
        component_text="After blocking, deal $1 Physical Damage.",
    )
    assert rows == ()
