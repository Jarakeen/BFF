from services.extreme_nightblade_shadow_passive_review import (
    IMPLEMENTED,
    INTEGRATION_PENDING,
    IRRELEVANT,
    ExtremeNightbladeShadowPassiveReview,
)


def test_shadow_review_covers_all_four_passives() -> None:
    review = ExtremeNightbladeShadowPassiveReview()
    rows = review.items()

    assert [row.passive_name for row in rows] == [
        "Refreshing Shadows",
        "Shadow Barrier",
        "Dark Vigor",
        "Dark Veil",
    ]
    assert len({row.passive_name for row in rows}) == 4


def test_only_dark_vigor_is_relevant_to_most_actual_heal() -> None:
    rows = ExtremeNightbladeShadowPassiveReview().items()
    relevant = [row for row in rows if row.objective_relevant]

    assert [(row.passive_name, row.coverage_status) for row in relevant] == [
        ("Dark Vigor", INTEGRATION_PENDING),
    ]
    assert all(
        row.coverage_status == IRRELEVANT
        for row in rows
        if not row.objective_relevant
    )


def test_shadow_review_remains_incomplete_until_dark_vigor_context_wiring() -> None:
    review = ExtremeNightbladeShadowPassiveReview()

    assert not review.complete
    assert all(row.coverage_status != IMPLEMENTED for row in review.items() if row.objective_relevant)
