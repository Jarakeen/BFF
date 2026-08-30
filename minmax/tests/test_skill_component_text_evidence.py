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


def test_meteor_marked_up_tick_interval_is_still_explicit_dot():
    text = (
        "After impact, enemies in the target area take |cffffff$2|r Flame Damage "
        "every |cffffff1|r second for |cffffff11|r seconds."
    )

    evidence = extract_component_text_evidence(text, 2)

    assert evidence.effect_kind == "damage"
    assert evidence.damage_type == "flame"
    assert evidence.is_dot is True
    assert evidence.is_aoe is True


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


def test_lotus_fan_initial_hit_is_aoe_when_enemies_around_you_are_explicit():
    text = (
        "Flash through the shadows and ambush an enemy while unleashing a fan of knives, "
        "dealing |cffffff$1|r Magic Damage to them and enemies around you."
    )

    evidence = extract_component_text_evidence(text, 1)

    assert evidence.effect_kind == "damage"
    assert evidence.damage_type == "magical"
    assert evidence.is_dot is False
    assert evidence.is_aoe is True


def test_lotus_fan_marked_up_over_time_component_is_aoe_dot():
    text = (
        "All enemies hit take an additional |cffffff$2|r Magic Damage over "
        "|cffffff5|r seconds and are afflicted with Minor Vulnerability."
    )

    evidence = extract_component_text_evidence(text, 2)

    assert evidence.effect_kind == "damage"
    assert evidence.damage_type == "magical"
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
    assert evidence.is_dot is None
    assert evidence.is_aoe is None


def test_absorb_missile_heal_amount_is_not_stolen_by_damage_condition_wording():
    text = (
        "While the shield persists, you are healed for |cffffff$2|r Health the next "
        "time a harmful direct damage projectile hits you."
    )

    evidence = extract_component_text_evidence(text, 2)

    assert evidence.effect_kind == "heal"
    assert evidence.damage_type is None
    assert evidence.is_dot is False
    assert evidence.is_aoe is False


def test_blood_craze_health_amount_is_heal_even_when_sentence_mentions_damage():
    text = "You heal for |cffffff$3|r Health anytime this ability deals damage."

    evidence = extract_component_text_evidence(text, 3)

    assert evidence.effect_kind == "heal"
    assert evidence.damage_type is None
    assert evidence.is_dot is False
    assert evidence.is_aoe is False


def test_elude_duration_coefficient_is_not_classified_as_damage():
    text = (
        "Shroud yourself in mist to gain Major Evasion, reducing damage taken from area "
        "attacks by 20% for |cffffff$1|r seconds."
    )

    evidence = extract_component_text_evidence(text, 1)

    assert evidence.effect_kind is None
    assert evidence.damage_type is None
    assert evidence.is_dot is None
    assert evidence.is_aoe is None


def test_ring_of_preservation_health_component_is_periodic_aoe_heal():
    text = (
        "You and your allies in the area gain Minor Protection and Minor Endurance, "
        "reducing damage taken by 5% and increasing Stamina Recovery by 15%, and are "
        "healed for |cffffff$1|r Health every 1 second."
    )

    evidence = extract_component_text_evidence(text, 1)

    assert evidence.effect_kind == "heal"
    assert evidence.damage_type is None
    assert evidence.is_dot is True
    assert evidence.is_aoe is True


def test_dark_talons_enemies_near_you_is_explicit_aoe():
    text = (
        "Call forth talons from the ground, dealing |cffffff$1|r Flame Damage to "
        "enemies near you and immobilizing them for 4 seconds."
    )

    evidence = extract_component_text_evidence(text, 1)

    assert evidence.effect_kind == "damage"
    assert evidence.damage_type == "flame"
    assert evidence.is_dot is False
    assert evidence.is_aoe is True


def test_reverberating_bash_delayed_additional_hit_is_direct_damage():
    text = "After the stun ends, the enemy takes an additional |cffffff$2|r Physical Damage."

    evidence = extract_component_text_evidence(text, 2)

    assert evidence.effect_kind == "damage"
    assert evidence.damage_type == "physical"
    assert evidence.is_dot is False
    assert evidence.is_aoe is False


def test_fire_rune_triggered_blast_is_direct_aoe_damage():
    text = "When triggered, the rune blasts all enemies in the target area for |cffffff$1|r Flame Damage."

    evidence = extract_component_text_evidence(text, 1)

    assert evidence.effect_kind == "damage"
    assert evidence.damage_type == "flame"
    assert evidence.is_dot is False
    assert evidence.is_aoe is True
