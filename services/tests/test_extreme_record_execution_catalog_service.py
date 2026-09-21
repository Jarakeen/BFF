from services.extreme_record_execution_catalog_service import (
    ExtremeRecordExecutionCatalogService,
    ExtremeRecordExecutionStatus,
)
from services.extreme_record_objective_catalog_service import EXTREME_RECORD_OBJECTIVES


def test_every_canonical_record_has_exactly_one_execution_disposition() -> None:
    rows = ExtremeRecordExecutionCatalogService.descriptors()

    assert len(rows) == len(EXTREME_RECORD_OBJECTIVES) == 32
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

    for key in ("actual_heal", "critical_heal"):
        assert rows[key].status is ExtremeRecordExecutionStatus.SPECIALIZED
        assert rows[key].execution_family == "actual-heal-event"

    for key in ("bash_damage", "damage_shield"):
        assert rows[key].status is ExtremeRecordExecutionStatus.SPECIALIZED
        assert rows[key].execution_family == "single-event-output"

    for key in ("resource_sustain", "ultimate_generation"):
        assert rows[key].status is ExtremeRecordExecutionStatus.SPECIALIZED
        assert rows[key].execution_family == "resource-timeline"

    for key in ("movement_speed", "sprint_speed", "stealthed_movement_speed"):
        assert rows[key].status is ExtremeRecordExecutionStatus.SPECIALIZED
        assert rows[key].execution_family == "movement-state"

    assert rows["detection_radius_reduction"].status is ExtremeRecordExecutionStatus.SPECIALIZED
    assert rows["detection_radius_reduction"].execution_family == "stealth-state"

    for key in ("invisibility_duration", "invisibility_uptime"):
        assert rows[key].status is ExtremeRecordExecutionStatus.SPECIALIZED
        assert rows[key].execution_family == "stealth-runtime"


def test_execution_disposition_counts_make_remaining_work_explicit() -> None:
    rows = ExtremeRecordExecutionCatalogService.descriptors()
    counts = {status: 0 for status in ExtremeRecordExecutionStatus}
    for row in rows:
        counts[row.status] += 1

    assert counts[ExtremeRecordExecutionStatus.READY] == 19
    assert counts[ExtremeRecordExecutionStatus.SPECIALIZED] == 12
    assert counts[ExtremeRecordExecutionStatus.PENDING] == 1
    sustained = ExtremeRecordExecutionCatalogService.descriptor("sustained_dps")
    assert sustained.status is ExtremeRecordExecutionStatus.PENDING
    assert sustained.execution_family == "combat-simulation"
