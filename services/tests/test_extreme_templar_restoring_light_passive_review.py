from __future__ import annotations

from services.extreme_templar_restoring_light_passive_review import (
    IMPLEMENTED,
    IRRELEVANT,
    ExtremeTemplarRestoringLightPassiveReview,
)


def test_restoring_light_review_covers_exact_live_u50_passive_roster() -> None:
    review = ExtremeTemplarRestoringLightPassiveReview()
    rows = review.items()

    assert tuple(row.passive_name for row in rows) == (
        "Mending",
        "Sacred Ground",
        "Light Weaver",
        "Master Ritualist",
    )
    assert review.complete


def test_restoring_light_relevant_passives_are_explicitly_modeled() -> None:
    rows = {
        row.passive_name: row
        for row in ExtremeTemplarRestoringLightPassiveReview().items()
    }

    assert rows["Mending"].objective_relevant
    assert rows["Mending"].coverage_status == IMPLEMENTED
    assert "ExtremeTemplarRestoringLightHealingService" in rows["Mending"].evidence
    assert "6%" in rows["Mending"].detail
    assert "13%" in rows["Mending"].detail

    assert rows["Sacred Ground"].objective_relevant
    assert rows["Sacred Ground"].coverage_status == IMPLEMENTED
    assert "ExtremeTemplarSacredGroundCombatStateService" in rows["Sacred Ground"].evidence
    assert "2 seconds" in rows["Sacred Ground"].detail
    assert "4 seconds" in rows["Sacred Ground"].detail


def test_restoring_light_utility_passives_do_not_change_most_actual_heal_size() -> None:
    rows = {
        row.passive_name: row
        for row in ExtremeTemplarRestoringLightPassiveReview().items()
    }

    assert not rows["Light Weaver"].objective_relevant
    assert rows["Light Weaver"].coverage_status == IRRELEVANT
    assert rows["Light Weaver"].evidence == "ExtremeTemplarLightWeaverService"
    assert "1/2 Ultimate" in rows["Light Weaver"].detail
    assert "30s/15s" in rows["Light Weaver"].detail

    assert not rows["Master Ritualist"].objective_relevant
    assert rows["Master Ritualist"].coverage_status == IRRELEVANT
