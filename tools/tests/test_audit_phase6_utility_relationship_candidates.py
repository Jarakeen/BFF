from tools.audit_phase6_utility_relationship_candidates import summarize, utility_kinds


def test_utility_kinds_extracts_multiple_explicit_relationships():
    kinds = utility_kinds(
        "The first attack reduces their Movement Speed by 30%, the second attack immobilizes them, "
        "and the third attack stuns them."
    )

    assert kinds == ("stun", "immobilize", "movement_speed_reduction")


def test_utility_kinds_covers_pull_knockback_taunt_and_interrupt_immunity():
    assert utility_kinds("Pull an enemy to you and taunt them.") == ("pull", "taunt")
    assert utility_kinds("Knock the enemy back 4 meters.") == ("knockback",)
    assert utility_kinds("Gain interrupt immunity while channeling.") == ("interrupt_immunity",)


def test_utility_kinds_does_not_promote_generic_damage_text():
    assert utility_kinds("Deal $1 Magic Damage to an enemy.") == ()


def test_summary_counts_multi_kind_and_unresolved_rows():
    from tools.audit_phase6_utility_relationship_candidates import UtilityCandidateRow

    rows = (
        UtilityCandidateRow(1, 1, 10, "A", ("stun",), "stuns"),
        UtilityCandidateRow(2, 1, 20, "B", ("stun", "immobilize"), "stuns and immobilizes"),
        UtilityCandidateRow(3, 1, 30, "C", (), "unknown utility"),
    )

    summary = summarize(rows)
    assert summary["rows"] == 3
    assert summary["unresolved"] == 1
    assert summary["multi_kind"] == 1
    assert summary["kinds"]["stun"] == 2
    assert summary["kinds"]["immobilize"] == 1
