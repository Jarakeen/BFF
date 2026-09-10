from services.extreme_sorcerer_daedric_summoning_passive_review import (
    IMPLEMENTED,
    IRRELEVANT,
    ExtremeSorcererDaedricSummoningPassiveReview,
)


def test_daedric_summoning_review_covers_all_four_passives() -> None:
    review = ExtremeSorcererDaedricSummoningPassiveReview()
    rows = review.items()

    assert [row.passive_name for row in rows] == [
        "Rebate",
        "Power Stone",
        "Daedric Protection",
        "Expert Summoner",
    ]
    assert len({row.passive_name for row in rows}) == 4


def test_only_expert_summoner_is_relevant_to_most_actual_heal() -> None:
    rows = ExtremeSorcererDaedricSummoningPassiveReview().items()
    relevant = [row for row in rows if row.objective_relevant]

    assert [(row.passive_name, row.coverage_status) for row in relevant] == [
        ("Expert Summoner", IMPLEMENTED),
    ]
    assert all(
        row.coverage_status == IRRELEVANT
        for row in rows
        if not row.objective_relevant
    )


def test_daedric_summoning_review_is_complete_with_explicit_pet_health_branch() -> None:
    review = ExtremeSorcererDaedricSummoningPassiveReview()
    row = next(row for row in review.items() if row.passive_name == "Expert Summoner")

    assert review.complete
    assert "5% Max Magicka and Max Stamina" in row.detail
    assert "5% Max Health" in row.detail
    assert "permanent pet" in row.detail
    assert "before canonical resource rounding" in row.detail
