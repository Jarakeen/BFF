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


def test_runtime_execution_strategy_resolution_is_catalogued() -> None:
    descriptor = SERVICE_CATALOG.get("rotation.runtime.execution_strategy_resolution")

    assert descriptor is not None
    assert descriptor.implementation_path == (
        "services.rotation_runtime_execution_strategy_service"
    )
    assert descriptor.dependencies == (
        "rotation.runtime.trigger_condition_resolution",
    )
    assert descriptor.responsibilities == (
        "rotation_runtime_execution_strategy_resolution",
    )
    assert descriptor.encounter_aware is True
    assert "RotationRuntimeActivatedIntent" in descriptor.inputs
    assert "PlayerBuild" in descriptor.inputs
    assert "RotationRuntimeExecutionStrategyCandidate" in descriptor.outputs
    assert "RotationRuntimeExecutionStrategyResolution" in descriptor.outputs


def test_runtime_executable_choice_resolution_is_catalogued() -> None:
    descriptor = SERVICE_CATALOG.get("rotation.runtime.executable_choice_resolution")

    assert descriptor is not None
    assert descriptor.implementation_path == (
        "services.rotation_runtime_executable_choice_service"
    )
    assert descriptor.dependencies == (
        "rotation.runtime.execution_strategy_resolution",
    )
    assert descriptor.responsibilities == (
        "rotation_runtime_executable_choice_resolution",
    )
    assert descriptor.encounter_aware is True
    assert "RotationPlan" in descriptor.inputs
    assert "RotationActionSlotRequirement" in descriptor.inputs
    assert "RotationActionTargetRequirement" in descriptor.inputs
    assert "RotationActionOccupancyRequirement" in descriptor.inputs
    assert "RotationRuntimeExecutableChoice" in descriptor.outputs
    assert "RotationRuntimeExecutableChoiceResolution" in descriptor.outputs


def test_runtime_action_materialization_is_catalogued() -> None:
    descriptor = SERVICE_CATALOG.get("rotation.runtime.action_materialization")

    assert descriptor is not None
    assert descriptor.implementation_path == (
        "services.rotation_runtime_action_materialization_service"
    )
    assert descriptor.dependencies == (
        "rotation.runtime.executable_choice_resolution",
    )
    assert descriptor.responsibilities == (
        "rotation_runtime_action_materialization",
    )
    assert descriptor.encounter_aware is True
    assert descriptor.inputs == (
        "RotationPlan",
        "RotationRuntimeExecutableChoice",
    )
    assert "RotationRuntimeActionMaterialization" in descriptor.outputs
    assert "RotationAction" in descriptor.outputs
    assert "RotationPlan" in descriptor.outputs
