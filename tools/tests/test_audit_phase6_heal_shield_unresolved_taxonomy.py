from tools.audit_phase6_heal_shield_unresolved_taxonomy import unresolved_category


def test_damage_linked_healing_is_not_treated_as_component_heal():
    assert unresolved_category(
        "Deal $1 Magic Damage and heal for 33% of the damage dealt.",
        1,
    ) == "damage_linked_healing"


def test_missing_health_healing_is_distinct_from_coefficient_heal():
    assert unresolved_category(
        "Deal $1 Magic Damage and heal you for 25% of your missing Health.",
        1,
    ) == "missing_health_healing"


def test_neighboring_heal_placeholder_is_detected():
    assert unresolved_category(
        "Deal $1 Flame Damage and you heal for $2 Health.",
        1,
    ) == "neighboring_heal_component"


def test_modifier_mentions_are_not_heal_or_shield_components():
    assert unresolved_category(
        "Deal $1 Flame Damage and reduce healing received and damage shield strength by 12%.",
        1,
    ) == "modifier_mention"


def test_current_restore_shorthand_remains_ambiguous():
    assert unresolved_category(
        "Current Restore: $2 While slotted you gain Major Vitality.",
        2,
    ) == "ambiguous_restore_shorthand"


def test_current_restore_shorthand_wins_over_vitality_modifier_mentions():
    assert unresolved_category(
        "Current Restore: $2 While slotted you gain Major Vitality, increasing healing received and damage shield strength by 12%.",
        2,
    ) == "ambiguous_restore_shorthand"
