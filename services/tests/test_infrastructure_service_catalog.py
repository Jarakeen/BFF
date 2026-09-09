from services.service_catalog import (
    ServiceAuthority,
    canonical_service_for,
    get_service,
)


def test_settings_persistence_owns_paths_and_secret_storage_boundary():
    service = canonical_service_for("application_settings_persistence")

    assert service is not None
    assert service.service_id == "infrastructure.settings.persistence"
    assert service.ui_safe is True
    assert "relative paths" in service.notes
    assert "OS keyring" in service.notes
    assert "settings.json" in service.notes


def test_application_update_preserves_user_owned_state_and_rejects_unsafe_archives():
    service = canonical_service_for("application_update_workflow")

    assert service is not None
    assert service.service_id == "infrastructure.application_update"
    assert "user-owned settings" in service.notes
    assert "eso.db progress" in service.notes
    assert "Archive traversal is rejected" in service.notes


def test_reference_update_orchestration_is_explicit_maintenance_not_app_updater():
    service = canonical_service_for("reference_update_task_orchestration")

    assert service is not None
    assert service.service_id == "maintenance.reference_update_orchestration"
    assert service.authority is ServiceAuthority.EXPERIMENTAL
    assert "Registering a task performs no work" in service.notes
    assert "not the end-user application updater" in service.notes


def test_archive_persistence_preserves_counter_compatibility_and_existing_ids():
    service = canonical_service_for("broadcast_archive_persistence")

    assert service is not None
    assert service.service_id == "broadcast.archive.persistence"
    assert service.ui_safe is True
    assert "OBS/Lua" in service.notes
    assert "does not allocate a new archive number" in service.notes


def test_infrastructure_services_are_distinct_capabilities():
    ids = {
        get_service("infrastructure.settings.persistence").service_id,
        get_service("infrastructure.application_update").service_id,
        get_service("maintenance.reference_update_orchestration").service_id,
        get_service("broadcast.archive.persistence").service_id,
    }

    assert ids == {
        "infrastructure.settings.persistence",
        "infrastructure.application_update",
        "maintenance.reference_update_orchestration",
        "broadcast.archive.persistence",
    }
