from services.service_catalog import EvidenceClass, canonical_service_for


def test_raid_plan_optimizer_adviser_is_canonical_read_only_capability() -> None:
    descriptor = canonical_service_for("raid_plan_read_only_optimization_advice")

    assert descriptor is not None
    assert descriptor.service_id == "raid_plan.optimizer_adviser"
    assert descriptor.implementation_path == "services.raid_plan_optimizer_adviser_service"
    assert descriptor.ui_safe is True
    assert descriptor.encounter_aware is False
    assert descriptor.evidence_class is EvidenceClass.MIXED
    assert "never mutate RaidPlan or saved builds" in descriptor.notes
