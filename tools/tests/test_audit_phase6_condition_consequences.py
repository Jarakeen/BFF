from tools.audit_phase6_condition_consequences import consequence_cues


def test_damage_consequence_cue_is_evidence_only():
    assert consequence_cues(
        "Deal $1 Magic Damage while the enemy is below 20% Health."
    ) == ("damage",)


def test_healing_and_shield_cues_can_coexist():
    assert consequence_cues(
        "While below 50% Health, heal for $1 Health and gain a damage shield."
    ) == ("damage", "healing", "shield")


def test_resource_cue_requires_resource_and_restore_or_gain_wording():
    assert consequence_cues(
        "Gain 1000 Magicka while the target is below 25% Health."
    ) == ("resource",)


def test_plain_condition_without_supported_consequence_stays_empty():
    assert consequence_cues(
        "This effect changes while the target is below 50% Health."
    ) == ()
