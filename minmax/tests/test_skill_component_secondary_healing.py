from minmax.skill_component_secondary_healing import (
    SecondaryHealingBasis,
    extract_explicit_secondary_healing,
)


def test_percent_of_damage_healing_is_supported():
    rows = extract_explicit_secondary_healing(
        skill_rank_id=1,
        coefficient_number=1,
        component_text="Deal $1 Magic Damage and heal for 33% of the damage dealt.",
    )
    assert len(rows) == 1
    assert rows[0].basis is SecondaryHealingBasis.DAMAGE_DEALT
    assert rows[0].fraction == 0.33


def test_full_damage_caused_healing_is_supported():
    rows = extract_explicit_secondary_healing(
        skill_rank_id=2,
        coefficient_number=2,
        component_text="Deal $2 Magic Damage and healing for the damage caused.",
    )
    assert len(rows) == 1
    assert rows[0].fraction == 1.0


def test_missing_health_healing_is_not_damage_linked():
    assert extract_explicit_secondary_healing(
        skill_rank_id=3,
        coefficient_number=1,
        component_text="Deal $1 Magic Damage and heal for 25% of your missing Health.",
    ) == ()


def test_neighboring_flat_heal_is_not_damage_linked():
    assert extract_explicit_secondary_healing(
        skill_rank_id=4,
        coefficient_number=1,
        component_text="Deal $1 Magic Damage and heal for $2 Health.",
    ) == ()
