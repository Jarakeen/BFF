from services.performance_raid_review_lokkestiiz_window_service import (
    PerformanceRaidReviewLokkestiizWindowService,
)
from services.rotation_lokkestiiz_landing_clock_service import (
    EncounterObservedClockBoundary,
)


def _boundary(*, occurrence: int, boundary: str, time_seconds: float, source: str = "ESO Logs"):
    return EncounterObservedClockBoundary(
        encounter_id="lokkestiiz",
        fact_key="aerial_onslaught_flight",
        boundary=boundary,
        occurrence=occurrence,
        time_seconds=time_seconds,
        source=source,
    )


def test_build_pairs_observed_begin_and_end_into_semantic_flight_window() -> None:
    result = PerformanceRaidReviewLokkestiizWindowService().build(
        report_code="ABC",
        fight_id=22,
        boundaries=(
            _boundary(occurrence=1, boundary="begin", time_seconds=21.024, source="flight entry"),
            _boundary(occurrence=1, boundary="end", time_seconds=72.683, source="boss damage resumed"),
        ),
    )

    assert result.ready is True
    assert len(result.windows) == 1
    window = result.windows[0]
    assert window.report_code == "ABC"
    assert window.fight_id == 22
    assert window.semantic_key == "aerial_onslaught_flight_1"
    assert window.label == "Aerial Onslaught Flight 1"
    assert window.start_seconds == 21.024
    assert window.end_seconds == 72.683
    assert "flight entry" in window.evidence_source
    assert "boss damage resumed" in window.evidence_source
    assert window.reviewed is True


def test_start_alias_is_accepted_as_begin_boundary() -> None:
    result = PerformanceRaidReviewLokkestiizWindowService().build(
        report_code="ABC",
        fight_id=22,
        boundaries=(
            _boundary(occurrence=2, boundary="start", time_seconds=98.326),
            _boundary(occurrence=2, boundary="end", time_seconds=161.703),
        ),
    )

    assert result.ready is True
    assert result.windows[0].semantic_key == "aerial_onslaught_flight_2"


def test_missing_pair_stays_explicitly_unresolved() -> None:
    result = PerformanceRaidReviewLokkestiizWindowService().build(
        report_code="ABC",
        fight_id=22,
        boundaries=(
            _boundary(occurrence=1, boundary="begin", time_seconds=21.024),
        ),
    )

    assert result.windows == ()
    assert result.ready is False
    assert "begin=1, end=0" in result.unresolved[0]


def test_duplicate_boundary_is_not_silently_selected() -> None:
    result = PerformanceRaidReviewLokkestiizWindowService().build(
        report_code="ABC",
        fight_id=22,
        boundaries=(
            _boundary(occurrence=1, boundary="begin", time_seconds=20.0),
            _boundary(occurrence=1, boundary="begin", time_seconds=21.0),
            _boundary(occurrence=1, boundary="end", time_seconds=72.0),
        ),
    )

    assert result.windows == ()
    assert "begin=2, end=1" in result.unresolved[0]


def test_non_lokkestiiz_or_other_fact_boundaries_are_ignored() -> None:
    other = EncounterObservedClockBoundary(
        encounter_id="yolnahkriin",
        fact_key="aerial_onslaught_flight",
        boundary="begin",
        occurrence=1,
        time_seconds=10.0,
        source="other boss",
    )
    wrong_fact = EncounterObservedClockBoundary(
        encounter_id="lokkestiiz",
        fact_key="some_other_fact",
        boundary="end",
        occurrence=1,
        time_seconds=20.0,
        source="wrong fact",
    )

    result = PerformanceRaidReviewLokkestiizWindowService().build(
        report_code="ABC",
        fight_id=22,
        boundaries=(other, wrong_fact),
    )

    assert result.windows == ()
    assert result.ready is False
    assert "No observed Lokkestiiz" in result.unresolved[0]


def test_end_at_or_before_begin_is_rejected() -> None:
    result = PerformanceRaidReviewLokkestiizWindowService().build(
        report_code="ABC",
        fight_id=22,
        boundaries=(
            _boundary(occurrence=3, boundary="begin", time_seconds=247.2),
            _boundary(occurrence=3, boundary="end", time_seconds=247.1),
        ),
    )

    assert result.windows == ()
    assert "ends at or before it begins" in result.unresolved[0]
