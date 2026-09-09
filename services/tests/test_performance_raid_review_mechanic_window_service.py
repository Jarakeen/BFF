from services.performance_raid_review_mechanic_window_service import (
    PerformanceRaidReviewMechanicWindowService,
    RaidReviewEncounterWindow,
)
from services.performance_raid_review_service import RaidReviewObservation


def _row(*, fight_id: int, actor_id: int, death_seconds: float | None, kill: bool = False):
    return RaidReviewObservation(
        report_code="A",
        fight_id=fight_id,
        fight_name="Lokkestiiz",
        kill=kill,
        actor_id=actor_id,
        actor_label=f"Player {actor_id}",
        role="Healer" if actor_id == 1 else "DPS",
        fight_duration_seconds=300.0,
        member_key=f"player-{actor_id}",
        death_count=1 if death_seconds is not None else 0,
        first_death_seconds=death_seconds,
    )


def _window(fight_id: int, key: str, label: str, start: float, end: float, *, reviewed=True):
    return RaidReviewEncounterWindow(
        report_code="A",
        fight_id=fight_id,
        semantic_key=key,
        label=label,
        start_seconds=start,
        end_seconds=end,
        evidence_source="reviewed runtime evidence",
        reviewed=reviewed,
    )


def test_repeated_earliest_deaths_create_raid_mechanic_window_finding() -> None:
    observations = [
        _row(fight_id=1, actor_id=1, death_seconds=73.0),
        _row(fight_id=1, actor_id=2, death_seconds=80.0),
        _row(fight_id=2, actor_id=1, death_seconds=74.0),
        _row(fight_id=3, actor_id=2, death_seconds=76.0),
    ]
    windows = [
        _window(1, "first_landing_recovery", "First Landing Recovery", 70.0, 85.0),
        _window(2, "first_landing_recovery", "First Landing Recovery", 70.0, 85.0),
        _window(3, "first_landing_recovery", "First Landing Recovery", 70.0, 85.0),
    ]

    findings = PerformanceRaidReviewMechanicWindowService().findings(observations, windows)

    raid = next(item for item in findings if item.scope == "raid")
    assert raid.category == "mechanic_window"
    assert raid.title == "First deaths repeatedly land in First Landing Recovery"
    assert "3/3 measured wipe pulls" in raid.evidence
    assert "not by itself proof" in raid.recommendation


def test_player_repeated_deaths_are_attributed_without_blame_claim() -> None:
    observations = [
        _row(fight_id=1, actor_id=1, death_seconds=73.0),
        _row(fight_id=2, actor_id=1, death_seconds=74.0),
    ]
    windows = [
        _window(1, "ice_cage_one", "Ice Cage One", 70.0, 80.0),
        _window(2, "ice_cage_one", "Ice Cage One", 70.0, 80.0),
    ]

    findings = PerformanceRaidReviewMechanicWindowService().findings(observations, windows)

    player = next(item for item in findings if item.scope == "player")
    assert player.subject == "Player 1"
    assert player.role == "Healer"
    assert player.title == "Repeated deaths occur during Ice Cage One"
    assert "before changing their build or base rotation" in player.recommendation


def test_unreviewed_windows_are_not_used_for_coaching() -> None:
    findings = PerformanceRaidReviewMechanicWindowService().findings(
        [
            _row(fight_id=1, actor_id=1, death_seconds=73.0),
            _row(fight_id=2, actor_id=1, death_seconds=74.0),
        ],
        [
            _window(1, "guess", "Guessed Window", 70.0, 80.0, reviewed=False),
            _window(2, "guess", "Guessed Window", 70.0, 80.0, reviewed=False),
        ],
    )

    assert findings == ()


def test_most_specific_overlapping_window_wins() -> None:
    findings = PerformanceRaidReviewMechanicWindowService().findings(
        [
            _row(fight_id=1, actor_id=1, death_seconds=75.0),
            _row(fight_id=2, actor_id=1, death_seconds=75.0),
        ],
        [
            _window(1, "flight_cycle", "Flight Cycle", 50.0, 100.0),
            _window(1, "ice_cage_one", "Ice Cage One", 70.0, 80.0),
            _window(2, "flight_cycle", "Flight Cycle", 50.0, 100.0),
            _window(2, "ice_cage_one", "Ice Cage One", 70.0, 80.0),
        ],
    )

    raid = next(item for item in findings if item.scope == "raid")
    assert "Ice Cage One" in raid.title


def test_reviewed_window_requires_semantic_identity() -> None:
    service = PerformanceRaidReviewMechanicWindowService()
    try:
        service.findings(
            [_row(fight_id=1, actor_id=1, death_seconds=75.0)],
            [_window(1, "", "Numeric 122820", 70.0, 80.0)],
        )
    except ValueError as exc:
        assert "semantic_key" in str(exc)
    else:
        raise AssertionError("reviewed mechanic windows must have semantic identity")
