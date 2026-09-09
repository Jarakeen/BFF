from services.performance_raid_review_service import (
    PerformanceRaidReviewService,
    RaidReviewObservation,
)


def _row(
    *,
    fight_id: int,
    kill: bool,
    actor_id: int = 1,
    actor_label: str = "Player",
    role: str = "DPS",
    output_total: float = 0.0,
    output_per_second: float = 0.0,
    boss_active_seconds: float | None = None,
    death_count: int = 0,
    first_death_ability: str = "",
    resource: float | None = None,
    uptimes: dict[str, float] | None = None,
) -> RaidReviewObservation:
    return RaidReviewObservation(
        report_code="report",
        fight_id=fight_id,
        fight_name="Lokkestiiz",
        kill=kill,
        actor_id=actor_id,
        actor_label=actor_label,
        role=role,
        fight_duration_seconds=300.0,
        output_total=output_total,
        output_per_second=output_per_second,
        boss_active_seconds=boss_active_seconds,
        death_count=death_count,
        first_death_ability=first_death_ability,
        minimum_primary_resource_percent=resource,
        key_uptimes=uptimes or {},
    )


def test_report_counts_unique_pulls_not_player_rows() -> None:
    report = PerformanceRaidReviewService().analyze(
        [
            _row(fight_id=1, kill=True, actor_id=1),
            _row(fight_id=1, kill=True, actor_id=2),
            _row(fight_id=2, kill=False, actor_id=1),
            _row(fight_id=2, kill=False, actor_id=2),
        ]
    )

    assert report.pull_count == 2
    assert report.kill_count == 1
    assert report.wipe_count == 1


def test_repeated_deaths_surface_before_throughput_blame() -> None:
    report = PerformanceRaidReviewService().analyze(
        [
            _row(fight_id=1, kill=False, death_count=1, first_death_ability="Ice Cage"),
            _row(fight_id=2, kill=False, death_count=1, first_death_ability="Ice Cage"),
            _row(fight_id=3, kill=False, death_count=0),
            _row(fight_id=4, kill=True, death_count=0),
        ]
    )

    finding = next(item for item in report.findings if item.category == "survival")
    assert finding.subject == "Player"
    assert "2/3 observed wipes" in finding.evidence
    assert "Ice Cage (2 pulls)" in finding.evidence
    assert "throughput" in finding.recommendation


def test_dd_output_uses_boss_active_time_when_available() -> None:
    report = PerformanceRaidReviewService().analyze(
        [
            _row(fight_id=1, kill=True, output_total=10_000_000, boss_active_seconds=100.0),
            _row(fight_id=2, kill=True, output_total=11_000_000, boss_active_seconds=100.0),
            _row(fight_id=3, kill=False, output_total=7_000_000, boss_active_seconds=100.0),
            _row(fight_id=4, kill=False, output_total=7_500_000, boss_active_seconds=100.0),
        ]
    )

    finding = next(item for item in report.findings if item.category == "damage")
    assert finding.priority == "medium"
    assert "kills 105,000/s" in finding.evidence
    assert "wipes 72,500/s" in finding.evidence
    assert "movement" in finding.recommendation


def test_higher_wipe_damage_does_not_get_called_a_rotation_failure() -> None:
    report = PerformanceRaidReviewService().analyze(
        [
            _row(fight_id=1, kill=True, output_per_second=90_000),
            _row(fight_id=2, kill=True, output_per_second=92_000),
            _row(fight_id=3, kill=False, output_per_second=110_000),
            _row(fight_id=4, kill=False, output_per_second=112_000),
        ]
    )

    finding = next(item for item in report.findings if item.category == "damage")
    assert finding.priority == "note"
    assert finding.title == "Raw damage is not the wipe signal"
    assert "survival" in finding.recommendation


def test_healer_throughput_alone_creates_no_higher_is_better_finding() -> None:
    report = PerformanceRaidReviewService().analyze(
        [
            _row(fight_id=1, kill=True, role="Healer", output_per_second=40_000),
            _row(fight_id=2, kill=True, role="Healer", output_per_second=42_000),
            _row(fight_id=3, kill=False, role="Healer", output_per_second=70_000),
            _row(fight_id=4, kill=False, role="Healer", output_per_second=75_000),
        ]
    )

    assert all(item.category != "damage" for item in report.findings)


def test_support_resource_pressure_is_timing_question_not_build_verdict() -> None:
    report = PerformanceRaidReviewService().analyze(
        [
            _row(fight_id=1, kill=True, role="Healer", resource=12.0),
            _row(fight_id=2, kill=False, role="Healer", resource=8.0),
            _row(fight_id=3, kill=False, role="Healer", resource=40.0),
        ]
    )

    finding = next(item for item in report.findings if item.category == "sustain")
    assert finding.role == "Healer"
    assert "15% or lower in 2/3" in finding.evidence
    assert "not proof that the build needs more recovery" in finding.recommendation


def test_key_uptime_comparison_calls_out_eligible_window_review() -> None:
    report = PerformanceRaidReviewService().analyze(
        [
            _row(fight_id=1, kill=True, role="Healer", uptimes={"Major Brittle": 92.0}),
            _row(fight_id=2, kill=True, role="Healer", uptimes={"Major Brittle": 90.0}),
            _row(fight_id=3, kill=False, role="Healer", uptimes={"Major Brittle": 65.0}),
            _row(fight_id=4, kill=False, role="Healer", uptimes={"Major Brittle": 68.0}),
        ]
    )

    finding = next(item for item in report.findings if item.category == "uptime")
    assert "Major Brittle" in finding.title
    assert "eligible encounter windows" in finding.recommendation
    assert "owns the effect obligation" in finding.recommendation


def test_other_encounters_are_filtered_out() -> None:
    other = RaidReviewObservation(
        report_code="report",
        fight_id=99,
        fight_name="Yolnahkriin",
        kill=False,
        actor_id=1,
        actor_label="Player",
        role="DPS",
        fight_duration_seconds=100.0,
        death_count=1,
    )

    report = PerformanceRaidReviewService().analyze(
        [_row(fight_id=1, kill=True), other],
        encounter_name="Lokkestiiz",
    )

    assert report.pull_count == 1
    assert report.kill_count == 1
    assert report.wipe_count == 0
