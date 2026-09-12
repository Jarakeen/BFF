from __future__ import annotations

"""Explicit build-persistence and saved-build capability catalog descriptors.

Metadata only. Runtime code keeps using typed imports and explicit wiring. These
entries document which layer owns canonical character/build state, which layer is
only a compatibility facade, and which legacy persistence implementation has been
superseded.
"""

from services.service_catalog import (
    EvidenceClass,
    ServiceAuthority,
    ServiceBehavior,
    ServiceDescriptor,
)


BUILD_SERVICE_DESCRIPTORS: tuple[ServiceDescriptor, ...] = (
    ServiceDescriptor(
        service_id="build.catalog.persistence",
        domain="build",
        purpose="Persist canonical character identity, reusable build records, and character-owned progression separately from ESO reference data.",
        implementation_path="services.build_catalog_service",
        inputs=("BuildRoster", "PlayerBuild", "CanonicalCharacterRecord"),
        outputs=("BuildCatalog", "CanonicalCharacterRecord", "CanonicalBuildRecord"),
        responsibilities=("canonical_character_build_persistence",),
        behavior=ServiceBehavior.DETERMINISTIC,
        evidence_class=EvidenceClass.NONE,
        notes="This is the authoritative character/build catalog. User-owned state lives outside eso.db; builds.json is compatibility data, not the source of truth.",
    ),
    ServiceDescriptor(
        service_id="build.compatibility.persistence_facade",
        domain="build",
        purpose="Expose the legacy BuildRoster/PlayerBuild persistence surface while mirroring writes into the canonical build catalog.",
        implementation_path="services.build_service",
        inputs=("BuildRoster", "PlayerBuild"),
        outputs=("BuildRoster",),
        dependencies=("build.catalog.persistence",),
        responsibilities=("build_roster_compatibility_persistence",),
        behavior=ServiceBehavior.DETERMINISTIC,
        ui_safe=True,
        evidence_class=EvidenceClass.NONE,
        notes="Compatibility/UI facade only. CanonicalBuildBridge makes the build catalog authoritative and keeps builds.json as a legacy mirror for existing tooling and exports.",
    ),
    ServiceDescriptor(
        service_id="build.legacy.canonical_persistence_v1",
        domain="build",
        purpose="Legacy version-1 canonical character/build JSON persistence retained only for historical compatibility.",
        implementation_path="services.canonical_build_service",
        inputs=("CanonicalCharacterRecord", "CanonicalBuildRecord"),
        outputs=("CanonicalBuildDocumentV1",),
        authority=ServiceAuthority.DEPRECATED,
        responsibilities=("legacy_canonical_build_persistence_v1",),
        behavior=ServiceBehavior.DETERMINISTIC,
        evidence_class=EvidenceClass.NONE,
        superseded_by="build.catalog.persistence",
        notes="No current repository consumers were found. BuildCatalogService plus CanonicalBuildBridge supersede this persistence path.",
    ),
    ServiceDescriptor(
        service_id="build.screenshot_evidence_staging",
        domain="build",
        purpose="Stage Armory and character-sheet screenshots as review-first build evidence without interpreting or mutating saved build state.",
        implementation_path="services.build_screenshot_import_service",
        inputs=("ArmoryScreenshot", "CharacterSheetScreenshot"),
        outputs=("BuildScreenshotIntake",),
        responsibilities=("build_screenshot_evidence_staging",),
        behavior=ServiceBehavior.DETERMINISTIC,
        ui_safe=True,
        evidence_class=EvidenceClass.OBSERVATIONAL,
        provenance=("User-supplied ESO screenshots",),
        notes="Staging only. Screenshot evidence remains awaiting analysis until reviewed; it does not write canonical build fields automatically.",
    ),
    ServiceDescriptor(
        service_id="build.saved_capability_analysis",
        domain="build",
        purpose="Resolve what an explicit saved build can canonically provide while preserving unresolved and runtime-only boundaries.",
        implementation_path="services.saved_build_capability_service",
        inputs=("PlayerBuild", "CanonicalEsoDatabase", "CharacterProgression"),
        outputs=("SavedBuildCapabilityAudit", "RaidCoverageSnapshot"),
        dependencies=("build.compatibility.persistence_facade",),
        responsibilities=("saved_build_static_capability_analysis",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=False,
        evidence_class=EvidenceClass.GAME_MECHANIC,
        notes="Static capability availability is not runtime uptime. Profile summaries do not assign providers. Dynamic CP, potion activation, conditional effects, and unresolved scribing semantics remain explicit boundaries rather than being inferred.",
    ),
)


__all__ = ["BUILD_SERVICE_DESCRIPTORS"]
