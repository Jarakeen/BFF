from __future__ import annotations

from services.performance_raid_review_service import (
    PerformanceRaidReviewService,
    RaidReviewObservation,
)


def test_single_pull_cannot_emit_cross_pull_pattern_findings() -> None:
    rows = [
        RaidReviewObservation(
            report_code="ABC",
            fight_id=7,
            fight_name="Xalvakka",
            kill=False,
            actor_id=actor_id,
            actor_label=label,
            role=role,
            fight_duration_seconds=180.0,
            member_key=f"abc:{actor_id}",
            output_per_second=output,
            death_count=1,
            first_death_seconds=75.0,
            first_death_ability="Corrupted Blast",
            minimum_primary_resource_percent=5.0,
            key_uptimes={"Major Courage": 40.0},
        )
        for actor_id, label, role, output in (
            (1, "Tank", "Tank", 10_000.0),
            (2, "Healer", "Healer", 30_000.0),
            (3, "DD", "DPS", 100_000.0),
        )
    ]

    report = PerformanceRaidReviewService().analyze(rows, encounter_name="Xalvakka")

    assert report.pull_count == 1
    assert report.kill_count == 0
    assert report.wipe_count == 1
    forbidden_categories = {
        "death_window",
        "survival",
        "damage",
        "sustain",
        "uptime",
    }
    assert not forbidden_categories.intersection(
        finding.category for finding in report.findings
    )
