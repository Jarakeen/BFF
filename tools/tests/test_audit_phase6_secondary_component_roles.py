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


def test_summarize_counts_categories():
    rows = (
        SecondaryComponentRoleAuditRow(1, 2, 10, "A", "explicit_additional_damage", "damage", "x"),
        SecondaryComponentRoleAuditRow(2, 2, 20, "B", "classification_leftover", "heal", "y"),
        SecondaryComponentRoleAuditRow(3, 1, 30, "C", "classification_leftover", "damage", "z"),
    )
    assert summarize(rows) == Counter({"classification_leftover": 2, "explicit_additional_damage": 1})
