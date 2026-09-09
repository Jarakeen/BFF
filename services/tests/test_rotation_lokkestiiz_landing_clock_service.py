from services.rotation_lokkestiiz_healer_scenario import (
    build_magrat_df_healer_lokkestiiz_scenario,
)
from services.rotation_lokkestiiz_landing_clock_service import (
    EncounterObservedClockBoundary,
    RotationLokkestiizLandingClockService,
)


def _landing(occurrence: int, time_seconds: float) -> EncounterObservedClockBoundary:
    return EncounterObservedClockBoundary(
        encounter_id="lokkestiiz",
        fact_key="aerial_onslaught_flight",
        boundary="end",
        occurrence=occurrence,
        time_seconds=time_seconds,
        source="observed pull",
    )


def test_three_observed_landing_clocks_resolve_for_three_cycle_scenario() -> None:
    scenario = build_magrat_df_healer_lokkestiiz_scenario()

    evidence = RotationLokkestiizLandingClockService().resolve(
        scenario=scenario,
        boundaries=(
            _landing(1, 42.0),
            _landing(2, 91.5),
            _landing(3, 143.0),
        ),
    )

    assert evidence.ready is True
    assert evidence.landing_times_seconds == (42.0, 91.5, 143.0)
    assert evidence.sources == ("observed pull", "observed pull", "observed pull")
    assert evidence.unresolved == ()


def test_health_thresholds_are_not_converted_into_missing_landing_clocks() -> None:
    scenario = build_magrat_df_healer_lokkestiiz_scenario()

    evidence = RotationLokkestiizLandingClockService().resolve(
        scenario=scenario,
        boundaries=(),
    )

    assert evidence.ready is False
    assert evidence.landing_times_seconds == ()
    assert any("observed=0, requested=3" in item for item in evidence.unresolved)


def test_wrong_encounter_or_fact_evidence_does_not_count_as_landing_clock() -> None:
    scenario = build_magrat_df_healer_lokkestiiz_scenario()

    evidence = RotationLokkestiizLandingClockService().resolve(
        scenario=scenario,
        boundaries=(
            EncounterObservedClockBoundary(
                encounter_id="yolnahkriin",
                fact_key="aerial_onslaught_flight",
                boundary="end",
                occurrence=1,
                time_seconds=42.0,
                source="wrong encounter",
            ),
            EncounterObservedClockBoundary(
                encounter_id="lokkestiiz",
                fact_key="ice_cage",
                boundary="end",
                occurrence=1,
                time_seconds=50.0,
                source="wrong fact",
            ),
        ),
    )

    assert evidence.landing_times_seconds == ()
    assert evidence.ready is False


def test_landing_occurrences_must_be_contiguous() -> None:
    scenario = build_magrat_df_healer_lokkestiiz_scenario()

    evidence = RotationLokkestiizLandingClockService().resolve(
        scenario=scenario,
        boundaries=(
            _landing(1, 42.0),
            _landing(3, 91.5),
            _landing(4, 143.0),
        ),
    )

    assert evidence.ready is False
    assert any("contiguous from 1" in item for item in evidence.unresolved)


def test_landing_clock_times_must_be_strictly_increasing() -> None:
    scenario = build_magrat_df_healer_lokkestiiz_scenario()

    evidence = RotationLokkestiizLandingClockService().resolve(
        scenario=scenario,
        boundaries=(
            _landing(1, 42.0),
            _landing(2, 42.0),
            _landing(3, 143.0),
        ),
    )

    assert evidence.ready is False
    assert any("strictly increasing" in item for item in evidence.unresolved)
