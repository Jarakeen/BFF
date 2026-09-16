from services.extreme_record_execution_catalog_service import (
    ExtremeRecordExecutionCatalogService,
    ExtremeRecordExecutionStatus,
)
from services.extreme_record_objective_catalog_service import EXTREME_RECORD_OBJECTIVES


def test_every_canonical_record_has_exactly_one_execution_disposition() -> None:
    rows = ExtremeRecordExecutionCatalogService.descriptors()

    assert len(rows) == len(EXTREME_RECORD_OBJECTIVES) == 31
    assert tuple(row.objective.key for row in rows) == tuple(
        objective.key for objective in EXTREME_RECORD_OBJECTIVES
    )


def test_ready_static_records_include_existing_stats_critical_healing_and_block() -> None:
    rows = {row.objective.key: row for row in ExtremeRecordExecutionCatalogService.descriptors()}

    for key in (
        "max_health",
        "max_magicka",
        "max_stamina",
        "weapon_damage",
        "spell_damage",
        "weapon_critical",
        "spell_critical",
        "critical_damage",
        "healing_done",
        "critical_healing",
        "block_mitigation",
        "block_cost_reduction",
    ):
        row = rows[key]
        assert row.status is ExtremeRecordExecutionStatus.READY
        assert row.execution_family == "shared-static-stat"
        assert row.executable_in_static_lab is True


def test_related_records_share_execution_families() -> None:
    rows = {row.objective.key: row for row in ExtremeRecordExecutionCatalogService.descriptors()}

    assert rows["actual_heal"].status is ExtremeRecordExecutionStatus.SPECIALIZED
    assert rows["critical_heal"].status is ExtremeRecordExecutionStatus.SPECIALIZED
    assert rows["actual_heal"].execution_family == "actual-heal-event"
    assert rows["critical_heal"].execution_family == "actual-heal-event"

    assert rows["bash_damage"].status is ExtremeRecordExecutionStatus.SPECIALIZED
    assert rows["damage_shield"].status is ExtremeRecordExecutionStatus.SPECIALIZED
    assert rows["bash_damage"].execution_family == "single-event-output"
    assert rows["damage_shield"].execution_family == "single-event-output"

    assert rows["resource_sustain"].execution_family == "resource-timeline"
    assert rows["ultimate_generation"].execution_family == "resource-timeline"

    for key in ("movement_speed", "sprint_speed", "stealthed_movement_speed"):
        assert rows[key].status is ExtremeRecordExecutionStatus.SPECIALIZED
        assert rows[key].execution_family == "movement-state"

    assert rows["detection_radius_reduction"].execution_family == "stealth-state"
    assert rows["invisibility_duration"].execution_family == "stealth-runtime"
    assert rows["invisibility_uptime"].execution_family == "stealth-runtime"


def test_execution_disposition_counts_make_remaining_work_explicit() -> None:
    rows = ExtremeRecordExecutionCatalogService.descriptors()
    counts = {status: 0 for status in ExtremeRecordExecutionStatus}
    for row in rows:
        counts[row.status] += 1

    assert counts[ExtremeRecordExecutionStatus.READY] == 19
    assert counts[ExtremeRecordExecutionStatus.SPECIALIZED] == 7
    assert counts[ExtremeRecordExecutionStatus.PENDING] == 5
