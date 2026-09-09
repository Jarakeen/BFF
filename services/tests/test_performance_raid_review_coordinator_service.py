from types import SimpleNamespace

from services.performance_raid_review_coordinator_service import (
    PerformanceRaidReviewCoordinatorService,
)
from services.performance_raid_review_event_enrichment_service import (
    RaidReviewEventEnrichment,
)
from services.performance_raid_review_landing_recovery_service import (
    RaidReviewLandingRecoveryObservation,
)
from services.performance_raid_review_mechanic_window_service import (
    RaidReviewEncounterWindow,
)
from services.performance_raid_review_observation_service import RaidReviewSource


class _Client:
    def __init__(self):
        self.fights = {
            ("A", 1): {
                "name": "Lokkestiiz",
                "kill": True,
                "startTime": 1000.0,
                "endTime": 11000.0,
            },
            ("A", 2): {
                "name": "Lokkestiiz",
                "kill": False,
                "startTime": 12000.0,
                "endTime": 22000.0,
            },
            ("A", 3): {
                "name": "Lokkestiiz",
                "kill": False,
                "startTime": 23000.0,
                "endTime": 33000.0,
            },
            ("A", 4): {
                "name": "Lokkestiiz",
                "kill": True,
                "startTime": 34000.0,
                "endTime": 44000.0,
            },
        }

    def get_fight(self, report_code, fight_id):
        return self.fights[(report_code, fight_id)]


class _PerformanceService:
    def __init__(self):
        self.client = _Client()

    def build_snapshot(self, report_code, fight_id, actor_id, actor_label, role, **kwargs):
        return SimpleNamespace(
            FightName="Lokkestiiz",
            Role=role,
            FightDurationSeconds=10.0,
            BossActiveSeconds=10.0,
            OutputTotal=1_000_000.0 if fight_id in {1, 4} else 700_000.0,
            OutputPerSecond=100_000.0 if fight_id in {1, 4} else 70_000.0,
            BuffUptimes=[],
            DebuffUptimes=[],
            RaidDebuffUptimes=[],
        )


class _EventProvider:
    def __init__(self):
        self.calls = []

    def resolve(self, source, fight):
        self.calls.append((source.report_code, source.fight_id, source.actor_id))
        return RaidReviewEventEnrichment(
            death_count=0 if fight.get("kill") else 1,
            first_death_seconds=None if fight.get("kill") else 8.5,
            first_death_ability="" if fight.get("kill") else "Ice Cage",
        )


def _recovery(fight_id: int, delay: float) -> RaidReviewLandingRecoveryObservation:
    return RaidReviewLandingRecoveryObservation(
        report_code="A",
        fight_id=fight_id,
        occurrence=1,
        actor_id=11,
        actor_label="Magrat",
        role="Healer",
        member_key="magrat",
        landing_seconds=70.0,
        recovery_seconds=70.0 + delay,
        delay_seconds=delay,
        signal_semantic_key="aggressive_horn_after_landing",
        signal_label="Aggressive Horn",
        evidence_ability_name="Aggressive Horn",
    )


def test_coordinator_collects_enriched_observations_then_analyzes() -> None:
    performance = _PerformanceService()
    provider = _EventProvider()
    service = PerformanceRaidReviewCoordinatorService(
        performance,
        event_provider=provider,
    )

    result = service.review(
        [
            RaidReviewSource("A", 1, 7, "DD One", "DPS", member_key="dd-one"),
            RaidReviewSource("A", 2, 7, "DD One", "DPS", member_key="dd-one"),
        ],
        encounter_name="Lokkestiiz",
    )

    assert result.report.encounter_name == "Lokkestiiz"
    assert result.report.pull_count == 2
    assert result.report.kill_count == 1
    assert result.report.wipe_count == 1
    assert result.unresolved == ()
    assert [row.death_count for row in result.collection.observations] == [0, 1]
    assert provider.calls == [("A", 1, 7), ("A", 2, 7)]


def test_coordinator_merges_explicit_reviewed_mechanic_window_findings() -> None:
    performance = _PerformanceService()
    service = PerformanceRaidReviewCoordinatorService(
        performance,
        event_provider=_EventProvider(),
    )

    result = service.review(
        [
            RaidReviewSource("A", 2, 7, "DD One", "DPS", member_key="dd-one"),
            RaidReviewSource("A", 3, 7, "DD One", "DPS", member_key="dd-one"),
        ],
        encounter_name="Lokkestiiz",
        mechanic_windows=[
            RaidReviewEncounterWindow(
                "A", 2, "first_landing_recovery", "First Landing Recovery", 8.0, 9.0,
                evidence_source="reviewed runtime evidence",
            ),
            RaidReviewEncounterWindow(
                "A", 3, "first_landing_recovery", "First Landing Recovery", 8.0, 9.0,
                evidence_source="reviewed runtime evidence",
            ),
        ],
    )

    finding = next(
        item for item in result.report.findings
        if item.scope == "raid" and item.category == "mechanic_window"
    )
    assert finding.title == "First deaths repeatedly land in First Landing Recovery"
    assert "2/2 measured wipe pulls" in finding.evidence


def test_coordinator_merges_cross_pull_landing_recovery_findings() -> None:
    performance = _PerformanceService()
    service = PerformanceRaidReviewCoordinatorService(
        performance,
        event_provider=_EventProvider(),
    )

    result = service.review(
        [
            RaidReviewSource("A", 1, 11, "Magrat", "Healer", member_key="magrat"),
            RaidReviewSource("A", 2, 11, "Magrat", "Healer", member_key="magrat"),
            RaidReviewSource("A", 3, 11, "Magrat", "Healer", member_key="magrat"),
            RaidReviewSource("A", 4, 11, "Magrat", "Healer", member_key="magrat"),
        ],
        encounter_name="Lokkestiiz",
        landing_recovery_observations=[
            _recovery(1, 0.5),
            _recovery(4, 0.7),
            _recovery(2, 2.0),
            _recovery(3, 2.4),
        ],
    )

    finding = next(
        item for item in result.report.findings
        if item.category == "landing_recovery" and "Aggressive Horn" in item.title
    )
    assert finding.subject == "Magrat"
    assert finding.priority == "medium"
    assert "kills 0.60s vs wipes 2.20s" in finding.evidence


def test_coordinator_preserves_collection_unresolved_messages() -> None:
    class _BrokenObservationService:
        def collect(self, sources):
            from services.performance_raid_review_observation_service import (
                RaidReviewCollectionResult,
            )
            return RaidReviewCollectionResult(
                observations=(),
                unresolved=("missing evidence",),
            )

    performance = _PerformanceService()
    service = PerformanceRaidReviewCoordinatorService(
        performance,
        observation_service=_BrokenObservationService(),
        event_provider=_EventProvider(),
    )

    result = service.review([], encounter_name="Lokkestiiz")

    assert result.report.pull_count == 0
    assert result.unresolved == ("missing evidence",)
