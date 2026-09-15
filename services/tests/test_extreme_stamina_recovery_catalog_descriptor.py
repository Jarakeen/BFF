from services.service_catalog import (
    EvidenceClass,
    ServiceBehavior,
    canonical_service_for,
    get_service,
)


def test_stamina_recovery_record_descriptor_is_discoverable() -> None:
    descriptor = get_service("extreme.stamina_recovery_record")

    assert descriptor is not None
    assert descriptor.domain == "extreme"
    assert descriptor.implementation_path == "services.extreme_stamina_recovery_record_service"
    assert descriptor.outputs == ("ExtremeRecordResult",)
    assert descriptor.responsibilities == ("extreme_stamina_recovery_record_projection",)
    assert descriptor.behavior is ServiceBehavior.DETERMINISTIC
    assert descriptor.ui_safe is True
    assert descriptor.evidence_class is EvidenceClass.MIXED
    assert canonical_service_for("extreme_stamina_recovery_record_projection") is descriptor
