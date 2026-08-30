from minmax.skill_component_text_evidence import extract_component_text_evidence


def test_combat_prayer_coefficient_one_is_explicit_immediate_aoe_heal():
    text = (
        "Slam your staff down to activate its blessings, healing you and your allies "
        "in front of you for |cffffff$1|r Health. Also grants Minor Berserk."
    )

    evidence = extract_component_text_evidence(text, 1)

    assert evidence.effect_kind == "heal"
    assert evidence.is_dot is False
    assert evidence.is_aoe is True
    assert evidence.damage_type is None
    assert evidence.can_crit is None


def test_meteor_initial_hit_is_explicit_flame_aoe_direct_damage():
    text = (
        "Call a comet down from the constellations to blast an enemy, dealing "
        "|cffffff$1|r Flame Damage to all enemies in the area, knocking them down. "
        "After impact, enemies in the target area take |cffffff$2|r Flame Damage "
        "every second for 11 seconds."
    )

    evidence = extract_component_text_evidence(text, 1)

    assert evidence.effect_kind == "damage"
    assert evidence.damage_type == "flame"
    assert evidence.is_dot is False
    assert evidence.is_aoe is True
    assert evidence.can_crit is None


def test_meteor_second_active_component_is_explicit_flame_aoe_dot():
    text = (
        "Call a comet down from the constellations to blast an enemy, dealing "
        "|cffffff$1|r Flame Damage to all enemies in the area, knocking them down. "
        "After impact, enemies in the target area take |cffffff$2|r Flame Damage "
        "every second for 11 seconds."
    )

    evidence = extract_component_text_evidence(text, 2)

    assert evidence.effect_kind == "damage"
    assert evidence.damage_type == "flame"
    assert evidence.is_dot is True
    assert evidence.is_aoe is True
    assert evidence.can_crit is None


def test_corrosive_armor_damage_component_uses_coefficient_aware_placeholder():
    text = (
        "Ignite the molten lava in your veins, limiting incoming damage to 6% of "
        "your Max Health and dealing |cffffff$1|r Flame Damage to nearby enemies "
        "each second for 10 seconds."
    )

    evidence = extract_component_text_evidence(text, 1)

    assert evidence.effect_kind == "damage"
    assert evidence.damage_type == "flame"
    assert evidence.is_dot is True
    assert evidence.is_aoe is True


def test_missing_coefficient_placeholder_does_not_borrow_neighbor_semantics():
    text = "Deal |cffffff$1|r Flame Damage to an enemy."

    evidence = extract_component_text_evidence(text, 2)

    assert evidence.fragment == ""
    assert evidence.effect_kind is None
    assert evidence.damage_type is None
    assert evidence.is_dot is None
    assert evidence.is_aoe is None


def test_damage_shield_is_not_misclassified_as_damage():
    text = "Surround yourself with a damage shield that absorbs |cffffff$1|r damage."

    evidence = extract_component_text_evidence(text, 1)

    assert evidence.effect_kind == "shield"
    assert evidence.damage_type is None
