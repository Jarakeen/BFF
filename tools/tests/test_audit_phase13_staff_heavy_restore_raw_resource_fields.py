from types import SimpleNamespace

from tools.audit_phase13_staff_heavy_restore_raw_resource_fields import _resource_raw_fields


def test_resource_raw_fields_keeps_only_resource_waste_and_max_keys_case_insensitively():
    event = SimpleNamespace(
        raw_event={
            "resourceChange": 4247,
            "resourceChangeType": 0,
            "otherResourceChange": 0,
            "maxResourceAmount": 34643,
            "waste": 0,
            "sourceID": 7,
            "targetID": 7,
            "abilityGameID": 32760,
        }
    )

    assert _resource_raw_fields(event) == {
        "resourceChange": 4247,
        "resourceChangeType": 0,
        "otherResourceChange": 0,
        "maxResourceAmount": 34643,
        "waste": 0,
    }
