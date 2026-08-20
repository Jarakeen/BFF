from services.minmax.combat_duration import calculate_duration


def test_no_duration_is_full_uptime():
    result = calculate_duration(
        duration=None,
        fight_duration=60,
    )

    assert result.duration == 0.0
    assert result.uptime == 1.0


def test_duration_shorter_than_fight():
    result = calculate_duration(
        duration=5,
        fight_duration=60,
    )

    assert result.duration == 5
    assert result.uptime == 5 / 60


def test_duration_cannot_exceed_full_uptime():
    result = calculate_duration(
        duration=120,
        fight_duration=60,
    )

    assert result.uptime == 1.0


def test_zero_duration_has_zero_uptime():
    result = calculate_duration(
        duration=0,
        fight_duration=60,
    )

    assert result.duration == 0.0
    assert result.uptime == 0.0


def test_negative_duration_has_zero_uptime():
    result = calculate_duration(
        duration=-5,
        fight_duration=60,
    )

    assert result.duration == 0.0
    assert result.uptime == 0.0


def test_unknown_fight_duration_assumes_active_effect():
    result = calculate_duration(
        duration=5,
        fight_duration=None,
    )

    assert result.duration == 5
    assert result.uptime == 1.0