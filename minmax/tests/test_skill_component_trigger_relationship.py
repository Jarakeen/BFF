from minmax.skill_component_trigger_relationship import (
    SkillComponentTriggerType,
    extract_explicit_component_trigger_relationships,
)


def _one(text: str, coefficient_number: int = 1):
    rows = extract_explicit_component_trigger_relationships(
        skill_rank_id=10,
        coefficient_number=coefficient_number,
        component_text=text,
    )
    assert len(rows) == 1
    return rows[0]


def test_trap_trigger_is_explicit_ability_trigger():
    row = _one("When triggered, the trap deals $1 Bleed Damage and an additional $2 Bleed Damage over 20 seconds.")
    assert row.trigger_type is SkillComponentTriggerType.ABILITY_TRIGGERED


def test_transformed_light_and_heavy_attacks_preserve_condition():
    row = _one(
        "While transformed, your Light Attacks and Heavy Attacks apply a bleed for $1 Bleed Damage over 4 seconds."
    )
    assert row.trigger_type is SkillComponentTriggerType.LIGHT_OR_HEAVY_ATTACK
    assert row.condition == "while_transformed"


def test_rune_cage_full_stun_duration():
    row = _one("Deals $1 Magic Damage if the stun lasts the full duration.")
    assert row.trigger_type is SkillComponentTriggerType.STUN_FULL_DURATION


def test_shattering_rocks_after_stun_ends():
    row = _one("After the stun ends, the target takes $1 Flame Damage and you heal for $2 Health.")
    assert row.trigger_type is SkillComponentTriggerType.STUN_ENDED


def test_volcanic_ward_after_shield_ends():
    row = _one("When the shield ends the latent heat warms the target, healing them for $2 Health.", 2)
    assert row.trigger_type is SkillComponentTriggerType.EFFECT_ENDED


def test_killers_blade_enemy_death_trigger():
    row = _one("Heals you for $2 if the enemy dies within 2 seconds of being struck.", 2)
    assert row.trigger_type is SkillComponentTriggerType.ENEMY_DIES_AFTER_STRIKE


def test_living_vines_target_damage_trigger():
    row = _one("The vines heal the target for $1 Health each time they take damage.")
    assert row.trigger_type is SkillComponentTriggerType.TARGET_TAKES_DAMAGE


def test_wildfire_embers_dot_end_trigger():
    row = _one(
        "When your Dragonknight damage over time effects end, you apply Wildfire Embers to the target, dealing $1 Flame Damage over 12 seconds."
    )
    assert row.trigger_type is SkillComponentTriggerType.DAMAGE_OVER_TIME_EFFECT_ENDED


def test_bare_when_does_not_promote_without_concrete_event():
    rows = extract_explicit_component_trigger_relationships(
        skill_rank_id=10,
        coefficient_number=1,
        component_text="When something happens, deal $1 Flame Damage.",
    )
    assert rows == ()
