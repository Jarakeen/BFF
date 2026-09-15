from __future__ import annotations

from tools.audit_extreme_e2_actual_heal_ordinary_gear_unresolved_drilldown import (
    classify_unresolved_pattern,
)


def test_classify_unresolved_pattern_separates_major_h1_debt_families() -> None:
    assert (
        classify_unresolved_pattern(
            "Set (5): active set bonus is not yet mechanic-mapped: gain 300 Weapon and Spell Damage"
        )
        == "weapon_spell_damage"
    )
    assert (
        classify_unresolved_pattern(
            "Set (5): active set bonus is not yet mechanic-mapped: increase your Critical Healing by 10%"
        )
        == "critical_healing"
    )
    assert (
        classify_unresolved_pattern(
            "Set (5): active set bonus is not yet mechanic-mapped: heal an ally for 1000 Health"
        )
        == "healing_or_heal_proc"
    )
    assert (
        classify_unresolved_pattern(
            "Set (5): active set bonus is not yet mechanic-mapped: something mysterious happens"
        )
        == "opaque_or_other_unmapped"
    )
