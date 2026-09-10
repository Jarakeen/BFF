from __future__ import annotations

import pytest

from services.extreme_nightblade_assassination_passive_review import (
    IRRELEVANT,
    ExtremeNightbladeAssassinationPassiveReview,
)


def test_assassination_review_is_complete_and_exact() -> None:
    review = ExtremeNightbladeAssassinationPassiveReview()
    rows = review.items()

    assert review.complete
    assert tuple(row.passive_name for row in rows) == review.PASSIVE_NAMES
    assert all(row.objective_relevant is False for row in rows)
    assert all(row.coverage_status == IRRELEVANT for row in rows)


def test_assassination_review_preserves_critical_chance_vs_magnitude_boundary() -> None:
    rows = {row.passive_name: row for row in ExtremeNightbladeAssassinationPassiveReview().items()}

    assert "Critical Chance" in rows["Master Assassin"].detail
    assert "Critical Chance" in rows["Pressure Points"].detail
    assert "Critical Damage" in rows["Hemorrhage"].detail
    assert "Critical Healing" in rows["Hemorrhage"].detail
    assert "sustain" in rows["Executioner"].detail


def test_assassination_review_fails_closed_if_roster_drifts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        ExtremeNightbladeAssassinationPassiveReview,
        "PASSIVE_NAMES",
        ("Master Assassin", "Executioner", "Pressure Points"),
    )

    with pytest.raises(ValueError, match="must exactly match"):
        ExtremeNightbladeAssassinationPassiveReview().items()
