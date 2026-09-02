from tools.audit_phase6_utility_candidates import utility_types


def test_utility_types_detects_explicit_control_effects():
    fragment = (
        "Their first attack reduces their Movement Speed by 30% and their second attack "
        "immobilizes them before the third attack stuns them."
    )
    assert utility_types(fragment) == ("stun", "immobilize", "movement_speed")


def test_utility_types_detects_pull_taunt_and_knockback():
    fragment = "Pull the enemy to you, taunt them, then knock them back."
    assert utility_types(fragment) == ("knockback", "pull", "taunt")


def test_utility_types_ignores_unrelated_damage_text():
    assert utility_types("Deal $1 Flame Damage every 1 second.") == ()
