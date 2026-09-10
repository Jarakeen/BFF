from services.extreme_sorcerer_dark_magic_passive_review import (
    IMPLEMENTED,
    IRRELEVANT,
    ExtremeSorcererDarkMagicPassiveReview,
)


def test_dark_magic_review_covers_exact_passive_roster():
    review = ExtremeSorcererDarkMagicPassiveReview()

    assert tuple(row.passive_name for row in review.items()) == (
        "Unholy Knowledge",
        "Blood Magic",
        "Persistence",
        "Exploitation",
    )
    assert review.complete
    assert review.implemented


def test_dark_magic_review_marks_blood_magic_implemented():
    rows = {
        row.passive_name: row
        for row in ExtremeSorcererDarkMagicPassiveReview().items()
    }

    assert rows["Blood Magic"].objective_relevant
    assert rows["Blood Magic"].coverage_status == IMPLEMENTED
    assert "Max-Health-scaled" in rows["Blood Magic"].detail
    assert "10%" in rows["Blood Magic"].detail
    assert "ranked" in rows["Blood Magic"].detail


def test_dark_magic_non_magnitude_passives_are_explicitly_irrelevant():
    rows = {
        row.passive_name: row
        for row in ExtremeSorcererDarkMagicPassiveReview().items()
    }

    for name in ("Unholy Knowledge", "Persistence", "Exploitation"):
        assert not rows[name].objective_relevant
        assert rows[name].coverage_status == IRRELEVANT

    assert "Critical chance" in rows["Exploitation"].detail
