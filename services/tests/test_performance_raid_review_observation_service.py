from types import SimpleNamespace

from services.performance_raid_review_observation_service import (
    PerformanceRaidReviewObservationService,
    RaidReviewSource,
)


class _Client:
    def __init__(self):
        self.fights = {
            ("A", 1): {"name": "Lokkestiiz", "kill": True},
            ("B", 2): {"name": "Lokkestiiz", "kill": False},
        }

    def get_fight(self, report_code, fight_id):
        return self.fights[(report_code, fight_id)]


class _PerformanceService:
    def __init__(self):
        self.client = _Client()
        self.calls = []

    def build_snapshot(
        self,
        report_code,
        fight_id,
        actor_id,
        actor_label,
        role,
        immunity_buff_name="",
        immunity_buff_kind="Buff",
    ):
        self.calls.append(
            (
                report_code,
                fight_id,
                actor_id,
                actor_label,
                role,
                immunity_buff_name,
                immunity_buff_kind,
            )
        )
        return SimpleNamespace(
            FightName="Lokkestiiz",
            Role=role,
            FightDurationSeconds=300.0,
            BossActiveSeconds=180.0,
            OutputTotal=9_000_000.0,
            OutputPerSecond=30_000.0,
            BuffUptimes=[SimpleNamespace(Name="Major Courage", UptimePercent=80.0)],
            DebuffUptimes=[SimpleNamespace(Name="Major Brittle", UptimePercent=75.0)],
            RaidDebuffUptimes=[
                SimpleNamespace(Name="Major Brittle", UptimePercent=90.0),
                SimpleNamespace(Name="Major Breach", UptimePercent=99.0),
            ],
        )


def test_collect_builds_fresh_observation_and_preserves_member_identity() -> None:
    performance = _PerformanceService()
    service = PerformanceRaidReviewObservationService(performance)

    result = service.collect(
        [
            RaidReviewSource(
                report_code="A",
                fight_id=1,
                actor_id=7,
                actor_label="Magrat",
                role="Healer",
                member_key="magrat",
                immunity_buff_name="Flying",
                immunity_buff_kind="Buff",
            )
        ]
    )

    assert result.unresolved == ()
    assert len(result.observations) == 1
    row = result.observations[0]
    assert row.kill is True
    assert row.member_key == "magrat"
    assert row.actor_id == 7
    assert row.boss_active_seconds == 180.0
    assert row.active_output_per_second == 50_000.0
    assert row.key_uptimes == {
        "Major Courage": 80.0,
        "Major Brittle": 90.0,
        "Major Breach": 99.0,
    }
    assert performance.calls[0][-2:] == ("Flying", "Buff")


def test_collect_keeps_failures_explicit_and_continues_other_sources() -> None:
    performance = _PerformanceService()
    service = PerformanceRaidReviewObservationService(performance)

    result = service.collect(
        [
            RaidReviewSource("missing", 999, 1, "Nobody", "DPS"),
            RaidReviewSource("B", 2, 42, "Magrat", "Healer", member_key="magrat"),
        ]
    )

    assert len(result.observations) == 1
    assert result.observations[0].kill is False
    assert len(result.unresolved) == 1
    assert "missing #999 Nobody" in result.unresolved[0]


def test_without_member_key_actor_identity_remains_report_local() -> None:
    performance = _PerformanceService()
    service = PerformanceRaidReviewObservationService(performance)

    result = service.collect(
        [
            RaidReviewSource("A", 1, 7, "Anonymous 7", "DPS"),
            RaidReviewSource("B", 2, 7, "Anonymous 7", "DPS"),
        ]
    )

    first, second = result.observations
    assert first.stable_member_key == "a:7"
    assert second.stable_member_key == "b:7"
    assert first.stable_member_key != second.stable_member_key
