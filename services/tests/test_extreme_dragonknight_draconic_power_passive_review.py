from services.extreme_dragonknight_draconic_power_passive_review import (
    IMPLEMENTED,
    IRRELEVANT,
    ExtremeDragonknightDraconicPowerPassiveReview,
)


def test_draconic_power_review_covers_all_four_live_passives() -> None:
    rows = ExtremeDragonknightDraconicPowerPassiveReview().items()

    assert [row.passive_name for row in rows] == [
        "Burnished Scales",
        "World in Ruin",
        "Elder Dragon",
        "The Storm Voice",
    ]
    assert len({row.passive_name for row in rows}) == 4


def test_only_elder_dragon_is_relevant_to_most_actual_heal() -> None:
    rows = ExtremeDragonknightDraconicPowerPassiveReview().items()
    relevant = [row for row in rows if row.objective_relevant]

    assert [(row.passive_name, row.coverage_status) for row in relevant] == [
        ("Elder Dragon", IMPLEMENTED),
    ]
    assert all(
        row.coverage_status == IRRELEVANT
        for row in rows
        if not row.objective_relevant
    )


def test_draconic_power_review_is_complete() -> None:
    review = ExtremeDragonknightDraconicPowerPassiveReview()

    assert review.complete
    elder = next(row for row in review.items() if row.passive_name == "Elder Dragon")
    assert "Minor Brutality" in elder.detail
    assert "no uptime is invented" in elder.detail
