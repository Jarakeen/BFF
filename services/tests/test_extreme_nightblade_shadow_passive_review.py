from services.extreme_nightblade_shadow_passive_review import (
    IMPLEMENTED,
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
        ("Dark Vigor", IMPLEMENTED),
    ]
    assert all(
        row.coverage_status == IRRELEVANT
        for row in rows
        if not row.objective_relevant
    )


def test_shadow_review_is_complete_after_dark_vigor_context_wiring() -> None:
    review = ExtremeNightbladeShadowPassiveReview()

    assert review.complete
    assert all(
        row.coverage_status in {IMPLEMENTED, IRRELEVANT}
        for row in review.items()
    )
