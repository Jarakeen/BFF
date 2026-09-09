from services.esologs_trending_service import (
    EsoLogsTrendingService,
    RoleTrendingSummary,
    TrendingItem,
)


def _summary(*rows: tuple[str, int], player_count: int = 10) -> RoleTrendingSummary:
    return RoleTrendingSummary(
        role="dps",
        player_count=player_count,
        gear_sets=tuple(
            TrendingItem(name=name, count=count, player_count=player_count)
            for name, count in rows
        ),
    )


def test_momentum_classifies_waves_cooling_arrivals_and_breakouts():
    previous = {
        "encounter_id": 99,
        "role": "dps",
        "player_count": 10,
        "sets": [
            {"name": "Stable 1", "count": 8, "percent": 80.0, "rank": 1},
            {"name": "Stable 2", "count": 7, "percent": 70.0, "rank": 2},
            {"name": "Cooling Set", "count": 6, "percent": 60.0, "rank": 3},
            {"name": "Stable 4", "count": 5, "percent": 50.0, "rank": 4},
            {"name": "Stable 5", "count": 5, "percent": 50.0, "rank": 5},
            {"name": "Stable 6", "count": 4, "percent": 40.0, "rank": 6},
            {"name": "Stable 7", "count": 4, "percent": 40.0, "rank": 7},
            {"name": "Stable 8", "count": 3, "percent": 30.0, "rank": 8},
            {"name": "Stable 9", "count": 3, "percent": 30.0, "rank": 9},
            {"name": "Stable 10", "count": 2, "percent": 20.0, "rank": 10},
            {"name": "Breakout Set", "count": 1, "percent": 10.0, "rank": 11},
            {"name": "Wave Set", "count": 1, "percent": 10.0, "rank": 12},
        ],
    }

    current = _summary(
        ("Stable 1", 8),
        ("Stable 2", 7),
        ("Breakout Set", 6),
        ("Stable 4", 5),
        ("Stable 5", 5),
        ("Stable 6", 4),
        ("Stable 7", 4),
        ("Stable 8", 3),
        ("Stable 9", 3),
        ("Stable 10", 2),
        ("Wave Set", 2),
        ("New Set", 2),
        ("Cooling Set", 1),
        player_count=10,
    )

    result = EsoLogsTrendingService._with_movement(current, previous)

    assert result.has_history is True
    assert [row.name for row in result.making_waves] == ["Wave Set"]
    assert [row.name for row in result.cooling_off] == ["Cooling Set"]
    assert [row.name for row in result.new_arrivals] == ["New Set"]
    assert [row.name for row in result.breakouts] == ["Breakout Set"]


def test_first_snapshot_does_not_invent_momentum():
    result = EsoLogsTrendingService._with_movement(
        _summary(("Some Set", 3), player_count=5),
        None,
    )

    assert result.has_history is False
    assert result.making_waves == ()
    assert result.cooling_off == ()
    assert result.new_arrivals == ()
    assert result.breakouts == ()
