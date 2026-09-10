from __future__ import annotations

from services.extreme_warden_winters_embrace_passive_review import (
    IRRELEVANT,
    ExtremeWardenWintersEmbracePassiveReview,
)


def test_winters_embrace_review_covers_exact_live_u50_passive_roster() -> None:
    review = ExtremeWardenWintersEmbracePassiveReview()
    rows = review.items()

    assert tuple(row.passive_name for row in rows) == (
        "Glacial Presence",
        "Frozen Armor",
        "Icy Aura",
        "Piercing Cold",
    )
    assert review.complete


def test_winters_embrace_passives_do_not_change_most_actual_heal_size() -> None:
    rows = ExtremeWardenWintersEmbracePassiveReview().items()

    assert all(not row.objective_relevant for row in rows)
    assert all(row.coverage_status == IRRELEVANT for row in rows)


def test_frozen_armor_review_preserves_non_healing_implementation_evidence() -> None:
    rows = {
        row.passive_name: row
        for row in ExtremeWardenWintersEmbracePassiveReview().items()
    }

    assert rows["Frozen Armor"].evidence == "WardenPassiveInputResolver"
    assert "defensive objectives" in rows["Frozen Armor"].detail
