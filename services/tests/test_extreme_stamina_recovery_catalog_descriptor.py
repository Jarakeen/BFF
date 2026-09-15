from services.extreme_recovery_catalog_descriptors import EXTREME_RECOVERY_SERVICE_DESCRIPTORS
from services.service_catalog import EvidenceClass, ServiceBehavior


def test_stamina_recovery_record_descriptor_is_discoverable() -> None:
    matches = tuple(
        row
        for row in EXTREME_RECOVERY_SERVICE_DESCRIPTORS
        if row.service_id == "extreme.stamina_recovery_record"
    )

    assert len(matches) == 1
    descriptor = matches[0]
    assert descriptor.domain == "extreme"
    assert descriptor.implementation_path == "services.extreme_stamina_recovery_record_service"
    assert descriptor.outputs == ("ExtremeRecordResult",)
    assert descriptor.responsibilities == ("extreme_stamina_recovery_record_projection",)
    assert descriptor.behavior is ServiceBehavior.DETERMINISTIC
    assert descriptor.ui_safe is True
    assert descriptor.evidence_class is EvidenceClass.MIXED
