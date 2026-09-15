from services.extreme_conditional_actual_heal_class_route_catalog_service import (
    ExtremeConditionalActualHealClassRouteCatalogService,
)
from services.extreme_runtime_condition_window import ExtremeRuntimeConditionWindow
from services.extreme_runtime_snapshot import ExtremeRuntimeSnapshot
from services.extreme_runtime_snapshot_conditional_actual_heal_optimization_service import (
    ExtremeRuntimeSnapshotConditionalActualHealOptimizationService,
    RESTORATION_HEAVY_POST_COMPLETION_CONDITION,
    SACRED_GROUND_CONDITION,
)


def _snapshot(*, at: float) -> ExtremeRuntimeSnapshot:
    return ExtremeRuntimeSnapshot(
        runtime_history=(
            ExtremeRuntimeConditionWindow(
                condition_id=RESTORATION_HEAVY_POST_COMPLETION_CONDITION,
                active_from_seconds=10.0,
                active_until_seconds=14.0,
                source_evidence="reviewed Essence Drain post-heavy window",
            ),
            ExtremeRuntimeConditionWindow(
                condition_id=SACRED_GROUND_CONDITION,
                active_from_seconds=9.0,
                active_until_seconds=13.0,
                source_evidence="reviewed Sacred Ground active/grace window",
                sequence=1,
            ),
        ),
        snapshot_time_seconds=at,
    )


def test_snapshot_adapter_derives_active_healer_condition_flags() -> None:
    service = ExtremeRuntimeSnapshotConditionalActualHealOptimizationService(
        target_health_fraction=0.25,
        runtime_snapshot=_snapshot(at=12.0),
    )

    assert service.fully_charged_restoration_heavy_attack_completed is True
    assert service.sacred_ground_window_active is True


def test_snapshot_adapter_does_not_claim_expired_windows() -> None:
    service = ExtremeRuntimeSnapshotConditionalActualHealOptimizationService(
        target_health_fraction=0.25,
        runtime_snapshot=_snapshot(at=15.0),
    )

    assert service.fully_charged_restoration_heavy_attack_completed is False
    assert service.sacred_ground_window_active is False


def test_legacy_flags_remain_compatible_without_snapshot_windows() -> None:
    service = ExtremeRuntimeSnapshotConditionalActualHealOptimizationService(
        target_health_fraction=0.25,
        fully_charged_restoration_heavy_attack_completed=True,
        sacred_ground_window_active=True,
    )

    assert service.fully_charged_restoration_heavy_attack_completed is True
    assert service.sacred_ground_window_active is True


def test_production_class_route_catalog_uses_snapshot_aware_optimizer() -> None:
    catalog = ExtremeConditionalActualHealClassRouteCatalogService(
        target_health_fraction=0.25,
        runtime_snapshot=_snapshot(at=12.0),
    )

    assert isinstance(
        catalog.optimizer,
        ExtremeRuntimeSnapshotConditionalActualHealOptimizationService,
    )
    assert catalog.fully_charged_restoration_heavy_attack_completed is True
    assert catalog.sacred_ground_window_active is True
