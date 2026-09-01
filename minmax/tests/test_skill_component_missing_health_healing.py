from minmax.skill_component_missing_health_healing import (
    extract_explicit_missing_health_healing,
)


def test_explicit_percent_of_missing_health_heal_is_supported():
    rows = extract_explicit_missing_health_healing(
        skill_rank_id=10,
        coefficient_number=1,
        component_text=(
            "Deal $1 Magic Damage and heal you for 25% of your missing Health every 1 second."
        ),
    )

    assert len(rows) == 1
    assert rows[0].fraction == 0.25


def test_joined_missing_health_wording_is_supported():
    rows = extract_explicit_missing_health_healing(
        skill_rank_id=11,
        coefficient_number=1,
        component_text="Deal $1 Magic Damage and healing you for 25% of your missingHealth.",
    )

    assert len(rows) == 1
    assert rows[0].fraction == 0.25


def test_damage_linked_healing_does_not_match_missing_health_basis():
    assert extract_explicit_missing_health_healing(
        skill_rank_id=12,
        coefficient_number=1,
        component_text="Deal $1 Magic Damage and heal for 45% of the damage caused.",
    ) == ()


def test_percent_of_max_health_does_not_match_missing_health_basis():
    assert extract_explicit_missing_health_healing(
        skill_rank_id=13,
        coefficient_number=1,
        component_text="Deal $1 Magic Damage and heal for 25% of your Max Health.",
    ) == ()


def test_invalid_percent_fails_closed():
    assert extract_explicit_missing_health_healing(
        skill_rank_id=14,
        coefficient_number=1,
        component_text="Deal $1 Magic Damage and heal for 125% of your missing Health.",
    ) == ()
