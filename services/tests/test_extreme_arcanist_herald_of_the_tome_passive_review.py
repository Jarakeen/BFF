from services.extreme_arcanist_herald_of_the_tome_passive_review import (
    IMPLEMENTED,
    IRRELEVANT,
    ExtremeArcanistHeraldOfTheTomePassiveReview,
)


def test_herald_review_covers_all_four_passives():
    rows = ExtremeArcanistHeraldOfTheTomePassiveReview().items()

    assert [row.passive_name for row in rows] == [
        "Fated Fortune",
        "Harnessed Quintessence",
        "Psychic Lesion",
        "Splintered Secrets",
    ]
    assert len({row.passive_name for row in rows}) == 4


def test_fated_fortune_and_harnessed_quintessence_are_healing_relevant():
    rows = ExtremeArcanistHeraldOfTheTomePassiveReview().items()
    relevant = [row for row in rows if row.objective_relevant]

    assert [(row.passive_name, row.coverage_status) for row in relevant] == [
        ("Fated Fortune", IMPLEMENTED),
        ("Harnessed Quintessence", IMPLEMENTED),
    ]
    assert all(
        row.coverage_status == IRRELEVANT
        for row in rows
        if not row.objective_relevant
    )


def test_herald_review_is_complete():
    assert ExtremeArcanistHeraldOfTheTomePassiveReview().complete
