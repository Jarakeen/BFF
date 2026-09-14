from services.service_catalog import SERVICE_CATALOG


def test_runtime_triggered_rotation_intent_service_is_catalogued() -> None:
    descriptor = SERVICE_CATALOG.get("rotation.runtime.triggered_intent_projection")

    assert descriptor is not None
    assert descriptor.implementation_path == (
        "services.rotation_runtime_triggered_intent_service"
    )
    assert descriptor.responsibilities == (
        "rotation_runtime_triggered_intent_projection",
    )
    assert descriptor.encounter_aware is True
    assert "RaidPlanTriggeredResponsibility" in descriptor.inputs
    assert "RotationRuntimeTriggeredIntent" in descriptor.outputs


def test_runtime_trigger_condition_resolution_is_catalogued() -> None:
    descriptor = SERVICE_CATALOG.get("rotation.runtime.trigger_condition_resolution")

    assert descriptor is not None
    assert descriptor.implementation_path == (
        "services.rotation_runtime_trigger_condition_service"
    )
    assert descriptor.dependencies == (
        "rotation.runtime.triggered_intent_projection",
    )
    assert descriptor.responsibilities == (
        "rotation_runtime_trigger_condition_resolution",
    )
    assert descriptor.encounter_aware is True
    assert "RotationRuntimeTriggeredIntent" in descriptor.inputs
    assert "RotationRuntimeTriggerObservation" in descriptor.inputs
    assert "RotationRuntimeActivatedIntent" in descriptor.outputs
    assert "RotationRuntimeTriggerResolution" in descriptor.outputs
