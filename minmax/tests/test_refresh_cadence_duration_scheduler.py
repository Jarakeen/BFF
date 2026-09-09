from __future__ import annotations

import pytest

from minmax.refresh_cadence_duration_scheduler import (
    RefreshCadenceDurationRotationScheduler,
    RotationRefreshIntervalPolicy,
)
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.rotation_recast import RotationRecastRule


def _plan() -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=4.0,
        actions=(
            RotationAction(0.0, 0, RotationActionKind.SKILL, "Long Buff", "front"),
            RotationAction(1.0, 0, RotationActionKind.SKILL, "Filler", "front"),
            RotationAction(2.0, 0, RotationActionKind.SKILL, "Long Buff", "front"),
            RotationAction(3.0, 0, RotationActionKind.SKILL, "Filler", "front"),
            RotationAction(4.0, 0, RotationActionKind.SKILL, "Long Buff", "front"),
        ),
    )


def test_refresh_cadence_can_deliberately_recast_after_verified_expiry() -> None:
    scheduler = RefreshCadenceDurationRotationScheduler(
        (
            RotationRefreshIntervalPolicy(
                skill_name="Long Buff",
                bar="front",
                interval_seconds=3.0,
                source="explicit 66.7% support uptime policy",
            ),
        )
    )

    refined = scheduler.refine(
        _plan(),
        (RotationRecastRule("Long Buff", 2.0, bar="front"),),
    )

    casts = [
        action.time_seconds
        for action in refined.actions
        if action.kind is RotationActionKind.SKILL and action.name == "Long Buff"
    ]
    assert casts == [0.0, 3.0]


def test_refresh_cadence_requires_matching_verified_duration_rule() -> None:
    scheduler = RefreshCadenceDurationRotationScheduler(
        (RotationRefreshIntervalPolicy("Unknown Buff", 3.0, bar="front"),)
    )

    with pytest.raises(ValueError, match="no verified duration rule"):
        scheduler.refine(
            _plan(),
            (RotationRecastRule("Long Buff", 2.0, bar="front"),),
        )


def test_refresh_cadence_rejects_interval_earlier_than_verified_expiry() -> None:
    scheduler = RefreshCadenceDurationRotationScheduler(
        (RotationRefreshIntervalPolicy("Long Buff", 1.5, bar="front"),)
    )

    with pytest.raises(ValueError, match="earlier than verified expiry"):
        scheduler.refine(
            _plan(),
            (RotationRecastRule("Long Buff", 2.0, bar="front"),),
        )


def test_refresh_cadence_rejects_conflicting_early_refresh_rule() -> None:
    scheduler = RefreshCadenceDurationRotationScheduler(
        (RotationRefreshIntervalPolicy("Long Buff", 2.0, bar="front"),)
    )

    with pytest.raises(ValueError, match="conflicts with an existing verified early-refresh lead"):
        scheduler.refine(
            _plan(),
            (
                RotationRecastRule(
                    "Long Buff",
                    2.0,
                    bar="front",
                    refresh_lead_seconds=0.5,
                ),
            ),
        )
