import pytest

from services.major_brittle_runtime_service import (
    ChillApplicationEvent,
    project_major_brittle_from_chilled,
)


def _chill(time_seconds, source, *, target="boss", sequence=0):
    return ChillApplicationEvent(
        time_seconds=time_seconds,
        source=source,
        target=target,
        sequence=sequence,
    )


def _project(events, **overrides):
    values = {
        "target": "boss",
        "encounter_duration_seconds": 10.0,
        "tundras_maw_active": True,
        "major_brittle_duration_seconds": 2.0,
        "evidence_complete": True,
    }
    values.update(overrides)
    return project_major_brittle_from_chilled(events, **values)


def test_multiple_chill_sources_refresh_one_major_brittle_timeline():
    result = _project(
        (
            _chill(0.0, "Elemental Susceptibility"),
            _chill(1.0, "Elemental Blockade"),
            _chill(2.5, "Frost Enchantment"),
            _chill(6.0, "Winter's Revenge"),
        )
    )

    assert result.resolved
    assert [(window.start_time_seconds, window.end_time_seconds) for window in result.windows] == [
        (0.0, 4.5),
        (6.0, 8.0),
    ]
    assert result.windows[0].sources == (
        "Elemental Blockade",
        "Elemental Susceptibility",
        "Frost Enchantment",
    )
    assert result.active_seconds == pytest.approx(6.5)
    assert result.uptime_fraction == pytest.approx(0.65)


def test_overlapping_sources_are_not_double_counted():
    result = _project(
        (
            _chill(1.0, "Elemental Blockade"),
            _chill(1.0, "Frost Enchantment", sequence=1),
        )
    )

    assert len(result.windows) == 1
    assert result.active_seconds == pytest.approx(2.0)
    assert result.application_count_by_source == (
        ("Elemental Blockade", 1),
        ("Frost Enchantment", 1),
    )


def test_projection_is_target_scoped_and_clips_to_encounter_end():
    result = _project(
        (
            _chill(9.0, "Elemental Susceptibility"),
            _chill(2.0, "Elemental Blockade", target="add"),
        )
    )

    assert [(window.start_time_seconds, window.end_time_seconds) for window in result.windows] == [
        (9.0, 10.0)
    ]
    assert result.active_seconds == pytest.approx(1.0)


def test_missing_tundras_maw_prevents_major_brittle():
    result = _project(
        (_chill(1.0, "Elemental Susceptibility"),),
        tundras_maw_active=False,
    )

    assert result.resolved
    assert result.windows == ()
    assert result.active_seconds == 0.0
    assert result.uptime_fraction == 0.0


def test_unknown_tundras_maw_state_does_not_claim_zero_uptime():
    result = _project((), tundras_maw_active=None)

    assert not result.resolved
    assert result.active_seconds is None
    assert result.uptime_fraction is None
    assert result.unresolved == ("tundras_maw_state_required",)


def test_incomplete_chill_evidence_preserves_windows_but_not_uptime_claim():
    result = _project(
        (_chill(1.0, "Frost Enchantment"),),
        evidence_complete=False,
    )

    assert not result.resolved
    assert len(result.windows) == 1
    assert result.active_seconds is None
    assert result.uptime_fraction is None
    assert result.unresolved == ("chilled_application_evidence_incomplete",)


@pytest.mark.parametrize(
    ("overrides", "message"),
    (
        ({"encounter_duration_seconds": 0.0}, "encounter duration"),
        ({"major_brittle_duration_seconds": 0.0}, "Major Brittle duration"),
        ({"target": ""}, "target"),
    ),
)
def test_projection_rejects_invalid_required_inputs(overrides, message):
    with pytest.raises(ValueError, match=message):
        _project((), **overrides)
