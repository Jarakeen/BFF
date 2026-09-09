from __future__ import annotations

"""Shared infrastructure service catalog descriptors.

Metadata only. These entries document stable application/platform ownership boundaries
without turning the catalog into a service locator. Runtime code continues to use typed
imports and explicit construction.
"""

from services.service_catalog import (
    EvidenceClass,
    ServiceAuthority,
    ServiceBehavior,
    ServiceDescriptor,
)


INFRASTRUCTURE_SERVICE_DESCRIPTORS: tuple[ServiceDescriptor, ...] = (
    ServiceDescriptor(
        service_id="infrastructure.settings.persistence",
        domain="infrastructure",
        purpose="Load and persist FoundryDock application settings while resolving configured paths and keeping the ESO Logs client secret out of ordinary settings JSON when OS keyring storage is available.",
        implementation_path="services.settings_service",
        inputs=("SettingsJson", "OperatingSystemKeyring"),
        outputs=("ApplicationSettings",),
        responsibilities=("application_settings_persistence",),
        behavior=ServiceBehavior.DETERMINISTIC,
        ui_safe=True,
        evidence_class=EvidenceClass.NONE,
        notes="Configured relative paths are resolved against the settings file location. ESO Logs client secrets prefer OS keyring storage and only fall back to settings.json when keyring storage is unavailable.",
    ),
    ServiceDescriptor(
        service_id="infrastructure.application_update",
        domain="infrastructure",
        purpose="Check GitHub Releases, download and validate update archives, stage portable payloads, and launch Windows in-place FoundryDock updates without overwriting user-owned state.",
        implementation_path="services.application_update_service",
        inputs=("ApplicationVersion", "GitHubRelease", "UpdateArchive"),
        outputs=("ApplicationUpdateInfo", "StagedUpdatePayload", "UpdateLog"),
        responsibilities=("application_update_workflow",),
        behavior=ServiceBehavior.DETERMINISTIC,
        ui_safe=True,
        evidence_class=EvidenceClass.NONE,
        provenance=("GitHub Releases metadata and packaged update archive",),
        notes="Update payloads intentionally exclude user-owned settings, builds, eso.db progress, and user_data. Archive traversal is rejected before extraction and only packaged FoundryDock installs can launch an in-place update.",
    ),
    ServiceDescriptor(
        service_id="maintenance.reference_update_orchestration",
        domain="maintenance",
        purpose="Register and explicitly run named reference-data maintenance tasks with structured success/failure and timing results.",
        implementation_path="services.update_service",
        inputs=("NamedMaintenanceTask",),
        outputs=("UpdateTaskResult", "UpdateSummary"),
        responsibilities=("reference_update_task_orchestration",),
        authority=ServiceAuthority.EXPERIMENTAL,
        behavior=ServiceBehavior.DETERMINISTIC,
        evidence_class=EvidenceClass.NONE,
        notes="Registering a task performs no work. Execution is explicit through run_update/run_all. This is maintenance orchestration, not the end-user application updater.",
    ),
    ServiceDescriptor(
        service_id="broadcast.archive.persistence",
        domain="broadcast",
        purpose="Assign stable sequential broadcast/archive identifiers and persist human-readable markdown archive records while preserving legacy counter-file compatibility.",
        implementation_path="services.archive_service",
        inputs=("ArchivePrefix", "ArchiveRecordLines", "CounterFiles"),
        outputs=("ArchiveId", "ArchiveMarkdownPath", "ArchiveRecord"),
        responsibilities=("broadcast_archive_persistence",),
        behavior=ServiceBehavior.DETERMINISTIC,
        ui_safe=True,
        evidence_class=EvidenceClass.NONE,
        notes="Counter filenames intentionally remain compatible with existing OBS/Lua consumers. Rewriting an existing archive does not allocate a new archive number.",
    ),
)


__all__ = ["INFRASTRUCTURE_SERVICE_DESCRIPTORS"]
