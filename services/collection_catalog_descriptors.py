from __future__ import annotations

"""Achievement-progress and collection workspace catalog descriptors.

Metadata only. These entries document the boundary between canonical ESO reference
records and user-owned completion/collection state. Runtime code keeps using typed
imports and explicit dependency wiring rather than catalog-driven service location.
"""

from services.service_catalog import EvidenceClass, ServiceBehavior, ServiceDescriptor


COLLECTION_SERVICE_DESCRIPTORS: tuple[ServiceDescriptor, ...] = (
    ServiceDescriptor(
        service_id="achievement.progress.persistence",
        domain="achievement",
        purpose="Persist profile-aware local achievement completion without attributing ambiguous legacy progress to a named person.",
        implementation_path="services.achievement_progress_service",
        inputs=("AchievementId", "AchievementProfile", "CompletionState"),
        outputs=("AchievementProgressProfile",),
        responsibilities=("achievement_progress_persistence",),
        behavior=ServiceBehavior.DETERMINISTIC,
        ui_safe=True,
        evidence_class=EvidenceClass.NONE,
        notes="Local profile progress is the source of truth for completion checkboxes. Legacy single-profile data is preserved under neutral Default ownership rather than guessed onto a person.",
    ),
    ServiceDescriptor(
        service_id="achievement.stats.summary",
        domain="achievement",
        purpose="Combine canonical achievement reference rows with local completion state into earned/possible count and point summaries.",
        implementation_path="services.achievement_stats_service",
        inputs=("AchievementReference", "AchievementProgressProfile"),
        outputs=("AchievementProgressSummary",),
        dependencies=("achievement.reference.sqlite", "achievement.progress.persistence"),
        responsibilities=("achievement_progress_summary",),
        behavior=ServiceBehavior.DETERMINISTIC,
        ui_safe=True,
        evidence_class=EvidenceClass.MIXED,
        notes="Summary math combines imported ESO reference data with user-owned completion state; it does not alter either source.",
    ),
    ServiceDescriptor(
        service_id="achievement.progress.export",
        domain="achievement",
        purpose="Export canonical achievement reference rows and profile completion state in round-trip-friendly CSV/XLSX formats.",
        implementation_path="services.achievement_progress_export_service",
        inputs=("AchievementReference", "AchievementProgressProfile", "ExportPath"),
        outputs=("AchievementProgressExport",),
        dependencies=("achievement.reference.sqlite", "achievement.progress.persistence"),
        responsibilities=("achievement_progress_export",),
        behavior=ServiceBehavior.DETERMINISTIC,
        ui_safe=True,
        evidence_class=EvidenceClass.MIXED,
        notes="Export is a presentation/portability boundary. It does not become an alternate progress authority merely because it can round-trip user state.",
    ),
    ServiceDescriptor(
        service_id="collectible.database.workspace",
        domain="collectible",
        purpose="Normalize imported ESO collectible reference records and persist collection-workspace progress in dedicated SQLite tables.",
        implementation_path="services.eso_collectible_database_service",
        inputs=("CanonicalEsoDatabase", "ImportedCollectibleEntity", "CollectibleProgress"),
        outputs=("CollectibleCatalog", "CollectibleProgress"),
        responsibilities=("collectible_workspace_database",),
        behavior=ServiceBehavior.DETERMINISTIC,
        ui_safe=True,
        evidence_class=EvidenceClass.MIXED,
        notes="Unlike pure reference readers, this workspace owns dedicated collectible schema/progress tables in SQLite. Canonical imported collectible evidence and user-owned progress remain conceptually distinct even though they share the database file.",
    ),
    ServiceDescriptor(
        service_id="collectible.profiled_progress",
        domain="collectible",
        purpose="Add named-profile ownership and conservative migration to the shared collectible catalog and progress workspace.",
        implementation_path="services.profiled_collectible_service",
        inputs=("CollectibleCatalog", "CollectibleProfile", "CollectibleProgress"),
        outputs=("ProfiledCollectibleProgress",),
        dependencies=("collectible.database.workspace",),
        responsibilities=("profiled_collectible_progress",),
        behavior=ServiceBehavior.DETERMINISTIC,
        ui_safe=True,
        evidence_class=EvidenceClass.MIXED,
        notes="The collectible catalog is shared; only ownership/progress is profile-specific. Existing unprofiled progress migrates conservatively to Default rather than being assigned to a person without evidence.",
    ),
    ServiceDescriptor(
        service_id="stickerbook.progress",
        domain="collectible",
        purpose="Track profile-aware Item Set Collection ownership over the canonical dropped-set catalog while preserving source-data gaps explicitly.",
        implementation_path="services.stickerbook_service",
        inputs=("CanonicalGearSetCatalog", "StickerbookProfile", "StickerbookPiece"),
        outputs=("StickerbookProgress", "StickerbookPiece"),
        responsibilities=("stickerbook_progress_tracking",),
        behavior=ServiceBehavior.DETERMINISTIC,
        ui_safe=True,
        evidence_class=EvidenceClass.MIXED,
        notes="Crafted sets are intentionally excluded from ESO stickerbook totals. Synthetic standard weapon identities fill collection-shape gaps only at the stickerbook boundary and do not mutate canonical source tables.",
    ),
)


__all__ = ["COLLECTION_SERVICE_DESCRIPTORS"]
