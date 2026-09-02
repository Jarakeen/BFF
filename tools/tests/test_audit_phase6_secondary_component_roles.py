from collections import Counter

from tools.audit_phase6_secondary_component_roles import (
    SecondaryComponentRoleAuditRow,
    secondary_role_category,
    summarize,
)


def test_secondary_role_category_finds_explicit_additional_damage():
    fragment = "Deal $1 Flame Damage, then an additional $2 Flame Damage over 20 seconds."
    assert secondary_role_category(fragment, 2, "damage") == "explicit_additional_damage"


def test_secondary_role_category_finds_explicit_followup_damage():
    fragment = "Deal $1 Magic Damage, then deal $2 Magic Damage to the same enemy."
    assert secondary_role_category(fragment, 2, "damage") == "explicit_followup_damage"


def test_secondary_role_category_finds_explicit_additional_heal():
    fragment = "Heal the target for $1 Health and also heals one other injured target for $2 Health."
    assert secondary_role_category(fragment, 2, "heal") == "explicit_additional_heal"


def test_secondary_role_category_keeps_plain_component_as_classification_leftover():
    assert secondary_role_category("Deal $1 Flame Damage.", 1, "damage") == "classification_leftover"


def test_secondary_role_category_marks_triggered_addon_damage_as_phase7_boundary():
    fragment = (
        "While active, dealing damage with Light and Heavy Attacks causes an additional "
        "$1 Flame Damage, up to once every 2 seconds."
    )
    assert secondary_role_category(fragment, 1, "damage") == "phase7_triggered_additional_damage"


def test_secondary_role_category_marks_next_attack_addon_as_phase7_boundary():
    fragment = (
        "Infuse your weapon with power, causing your next Light Attack used within 2 seconds "
        "to deal an additional $1 Physical Damage."
    )
    assert secondary_role_category(fragment, 1, "damage") == "phase7_triggered_additional_damage"


def test_summarize_counts_categories():
    rows = (
        SecondaryComponentRoleAuditRow(1, 2, 10, "A", "explicit_additional_damage", "damage", "x"),
        SecondaryComponentRoleAuditRow(2, 2, 20, "B", "classification_leftover", "heal", "y"),
        SecondaryComponentRoleAuditRow(3, 1, 30, "C", "classification_leftover", "damage", "z"),
    )
    assert summarize(rows) == Counter({"classification_leftover": 2, "explicit_additional_damage": 1})
