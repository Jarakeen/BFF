from services.performance_boss_activity import invert_immune_windows


def _pairs(windows):
    return [(row.StartSeconds, row.EndSeconds) for row in windows]


def test_invert_immune_windows_returns_full_fight_when_no_immunity_windows() -> None:
    assert _pairs(invert_immune_windows([], duration_seconds=60.0)) == [(0.0, 60.0)]


def test_invert_immune_windows_returns_damageable_gaps() -> None:
    result = invert_immune_windows(
        [(10.0, 20.0), (35.0, 45.0)],
        duration_seconds=60.0,
    )
    assert _pairs(result) == [(0.0, 10.0), (20.0, 35.0), (45.0, 60.0)]


def test_invert_immune_windows_merges_overlaps_and_clips_to_fight() -> None:
    result = invert_immune_windows(
        [(-5.0, 12.0), (10.0, 18.0), (55.0, 75.0)],
        duration_seconds=60.0,
    )
    assert _pairs(result) == [(18.0, 55.0)]
