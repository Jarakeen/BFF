from tools.audit_phase6_richer_semantics_taxonomy import richer_category


def test_stored_damage_scaling_is_distinct_from_generic_conditional():
    assert richer_category(
        "After the duration ends, the sunlight bursts, dealing $2 Magic Damage, which increases based on the amount of damage you dealt to them over the duration, up to 200%.",
        2,
        "damage",
    ) == "stored_damage_scaling"


def test_per_tick_damage_ramp_is_distinct_from_generic_conditional():
    assert richer_category(
        "While in the area, enemies take $1 Magic Damage every 2 seconds for 20 seconds which increases by 12% per tick.",
        1,
        "damage",
    ) == "per_tick_damage_ramp"


def test_direct_heal_with_target_gap_is_not_invented_as_new_semantics():
    assert richer_category(
        "Also heals one other injured target for $2 Health.",
        2,
        "heal",
    ) == "direct_heal_classification_gap"


def test_multiple_damage_coefficients_can_be_classification_only():
    assert richer_category(
        "Blast up to three enemies with a charge of radiant heat, dealing $1 Flame Damage, an additional $2 Flame Damage over 20 seconds.",
        2,
        "damage",
    ) == "multi_damage_classification_gap"


def test_explicit_crowd_control_is_utility_relationship_candidate():
    assert richer_category(
        "Its arrival deals $1 Shock Damage and stuns enemies for 3 seconds.",
        1,
        "damage",
    ) == "utility_relationship_candidate"
