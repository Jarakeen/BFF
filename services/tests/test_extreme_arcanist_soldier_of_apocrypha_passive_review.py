from services.extreme_arcanist_soldier_of_apocrypha_passive_review import (
    IRRELEVANT,
    ExtremeArcanistSoldierOfApocryphaPassiveReview,
)


def test_soldier_review_covers_all_four_passives():
    rows = ExtremeArcanistSoldierOfApocryphaPassiveReview().items()

    assert [row.passive_name for row in rows] == [
        "Aegis of the Unseen",
        "Wellspring of the Abyss",
        "Circumvented Fate",
        "Implacable Outcome",
    ]
    assert len({row.passive_name for row in rows}) == 4


def test_soldier_passives_are_not_relevant_to_most_actual_heal():
    rows = ExtremeArcanistSoldierOfApocryphaPassiveReview().items()

    assert not any(row.objective_relevant for row in rows)
    assert all(row.coverage_status == IRRELEVANT for row in rows)


def test_soldier_review_is_complete():
    assert ExtremeArcanistSoldierOfApocryphaPassiveReview().complete
