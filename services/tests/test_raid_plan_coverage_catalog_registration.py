from services.service_catalog import get_service


def test_raid_plan_coverage_scope_service_is_registered() -> None:
    descriptor = get_service("raid_plan.coverage_scope")

    assert descriptor is not None
    assert descriptor.domain == "raid_plan"
    assert descriptor.implementation_path == "services.raid_plan_coverage_scope_service"
    assert descriptor.ui_safe is True
    assert "raid_plan_coverage_scope_resolution" in descriptor.responsibilities
