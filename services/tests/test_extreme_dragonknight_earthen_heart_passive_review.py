from services.extreme_dragonknight_earthen_heart_passive_review import (
    IRRELEVANT,
    ExtremeDragonknightEarthenHeartPassiveReview,
)


def test_earthen_heart_review_covers_current_four_passives() -> None:
    rows = ExtremeDragonknightEarthenHeartPassiveReview().items()

    assert [row.passive_name for row in rows] == [
        "Heart of Stone",
        "Landslide",
        "Blessing at the Peak",
        "Mountain Giant",
    ]
    assert len({row.passive_name for row in rows}) == 4


def test_no_earthen_heart_passive_enlarges_most_actual_heal() -> None:
    rows = ExtremeDragonknightEarthenHeartPassiveReview().items()

    assert all(not row.objective_relevant for row in rows)
    assert all(row.coverage_status == IRRELEVANT for row in rows)


def test_earthen_heart_review_distinguishes_passives_from_active_skill_mending() -> None:
    review = ExtremeDragonknightEarthenHeartPassiveReview()

    assert review.complete
    assert "active-skill" in review.__doc__
    assert "ExtremeDragonknightEarthenHeartMendingService" in review.__doc__
