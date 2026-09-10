from types import SimpleNamespace

from services.performance_raid_review_landing_recovery_service import RaidReviewLandingRecoveryObservation
from services.performance_raid_review_lokkestiiz_pull_service import LokkestiizPullRaidReviewEvidence
from services.performance_raid_review_lokkestiiz_session_service import (
    LokkestiizRaidReviewPullRequest,
    PerformanceRaidReviewLokkestiizSessionService,
)
from services.performance_raid_review_mechanic_window_service import RaidReviewEncounterWindow
from services.performance_raid_review_observation_service import RaidReviewSource
from services.rotation_lokkestiiz_landing_clock_service import EncounterObservedClockBoundary


class _Client:
    def get_fight(self, report_code, fight_id):
        return {"name": "Lokkestiiz", "startTime": 0.0, "endTime": 80_000.0}


class _Performance:
    def __init__(self):
        self.client = _Client()


class _Events:
    def __init__(self, rows):
        self.rows = tuple(rows)
        self.calls = 0

    def events_for_fight(self, **kwargs):
        self.calls += 1
        return self.rows


class _Pull:
    def build(self, **kwargs):
        window = RaidReviewEncounterWindow(
            report_code="A",
            fight_id=1,
            semantic_key="aerial_onslaught_flight_1",
            label="Aerial Onslaught Flight 1",
            start_seconds=5.0,
            end_seconds=60.0,
            evidence_source="reviewed flight evidence",
        )
        boundary = EncounterObservedClockBoundary(
            encounter_id="lokkestiiz",
            fact_key="aerial_onslaught_flight",
            boundary="end",
            occurrence=1,
            time_seconds=60.0,
            source="reviewed flight evidence",
        )
        return LokkestiizPullRaidReviewEvidence(
            boundaries=(boundary,),
            mechanic_windows=(window,),
            recovery_observations=(),
            unresolved=(),
        )


class _Coordinator:
    def __init__(self):
        self.calls = []

    def review(self, sources, **kwargs):
        self.calls.append((tuple(sources), kwargs))
        return SimpleNamespace(
            unresolved=(),
            report=SimpleNamespace(encounter_name="Lokkestiiz"),
            collection=SimpleNamespace(observations=()),
        )


def _damage(seconds, *, source=7, target=99, amount=1000):
    return {
        "timestamp": seconds * 1000.0,
        "type": "damage",
        "sourceID": source,
        "targetID": target,
        "amount": amount,
    }


def test_session_excludes_reviewed_flight_from_dd_ground_continuity() -> None:
    events = _Events([_damage(2.0), _damage(4.0), _damage(61.0), _damage(62.0)])
    coordinator = _Coordinator()
    service = PerformanceRaidReviewLokkestiizSessionService(
        _Performance(),
        event_provider=events,
        pull_service=_Pull(),
        coordinator_service=coordinator,
    )

    source = RaidReviewSource("A", 1, 7, "DD One", "DPS", member_key="dd-one")
    result = service.review([LokkestiizRaidReviewPullRequest("A", 1, 99, (source,))])

    assert events.calls == 1
    assert len(result.dd_ground_continuity) == 1
    observation = result.dd_ground_continuity[0]
    assert observation.measured_gap_count == 2
    assert observation.inactivity_gap_count == 0
    assert observation.longest_inactivity_seconds == 0.0
    _sources, kwargs = coordinator.calls[0]
    assert kwargs["dd_ground_continuity_observations"] == result.dd_ground_continuity


def test_session_passes_explicit_dd_inactivity_threshold_to_measurement() -> None:
    events = _Events([_damage(1.0), _damage(3.0), _damage(61.0), _damage(63.0)])
    service = PerformanceRaidReviewLokkestiizSessionService(
        _Performance(),
        event_provider=events,
        pull_service=_Pull(),
        coordinator_service=_Coordinator(),
    )

    source = RaidReviewSource("A", 1, 7, "DD One", "DPS", member_key="dd-one")
    result = service.review(
        [LokkestiizRaidReviewPullRequest("A", 1, 99, (source,))],
        dd_inactivity_threshold_seconds=1.5,
    )

    observation = result.dd_ground_continuity[0]
    assert observation.inactivity_threshold_seconds == 1.5
    assert observation.inactivity_gap_count == 2
    assert observation.inactivity_windows == ((1.0, 3.0), (61.0, 63.0))


def test_healer_only_pull_does_not_emit_spurious_missing_dd_message() -> None:
    service = PerformanceRaidReviewLokkestiizSessionService(
        _Performance(),
        event_provider=_Events([]),
        pull_service=_Pull(),
        coordinator_service=_Coordinator(),
    )

    source = RaidReviewSource("A", 1, 11, "Healer One", "Healer", member_key="healer-one")
    result = service.review([LokkestiizRaidReviewPullRequest("A", 1, 99, (source,))])

    assert result.dd_ground_continuity == ()
    assert not any("No DPS actors were supplied" in message for message in result.unresolved)
