from __future__ import annotations

"""Collection and achievement import/sync adapter catalog descriptors.

Metadata only. These services move user-owned progress between external/local workbook
representations and BFF. They are adapters, not alternate canonical progress stores.
"""

from services.service_catalog import EvidenceClass, ServiceBehavior, ServiceDescriptor


COLLECTION_SYNC_SERVICE_DESCRIPTORS: tuple[ServiceDescriptor, ...] = (
    ServiceDescriptor(
        service_id="achievement.workbook.local_import",
        domain="achievement",
        purpose="Read legacy BFF or Foundry-native local workbooks into achievement-progress snapshots without Google APIs.",
        implementation_path="services.local_achievement_workbook_service",
        inputs=("AchievementWorkbook", "AchievementProfileSource"),
        outputs=("GoogleSheetAchievementSnapshot",),
        responsibilities=("local_achievement_workbook_import",),
        behavior=ServiceBehavior.DETERMINISTIC,
        ui_safe=True,
        evidence_class=EvidenceClass.NONE,
        notes="This adapter reads progress evidence from .xlsx/.xlsm files. It does not become the achievement completion authority; imported snapshots must be reconciled into achievement.progress.persistence explicitly.",
    ),
    ServiceDescriptor(
        service_id="collectible.workbook.local_import",
        domain="collectible",
        purpose="Extract collectible ownership checkmarks from historical BFF workbook sections without treating workbook layout as canonical collection data.",
        implementation_path="services.local_collectible_workbook_service",
        inputs=("LegacyBffWorkbook", "CollectionProfileSource"),
        outputs=("LocalCollectibleSnapshot",),
        responsibilities=("local_collectible_workbook_import",),
        behavior=ServiceBehavior.DETERMINISTIC,
        ui_safe=True,
        evidence_class=EvidenceClass.NONE,
        notes="Only explicitly recognized collectible sheets and R/J ownership blocks are scanned. Motifs, recipes, titles, antiquities, stickerbook, and other checkmark sheets remain outside this adapter and keep their own progress systems.",
    ),
    ServiceDescriptor(
        service_id="collectible.motif.workbook_import",
        domain="collectible",
        purpose="Extract profile-aware historical motif completion rows from the legacy BFF motif sheets.",
        implementation_path="services.local_motif_workbook_service",
        inputs=("LegacyBffWorkbook", "CollectionProfileSource"),
        outputs=("LocalMotifSnapshot",),
        responsibilities=("local_motif_workbook_import",),
        behavior=ServiceBehavior.DETERMINISTIC,
        ui_safe=True,
        evidence_class=EvidenceClass.NONE,
        notes="The historical workbook records completion at whole-motif row level for this importer. Chapter columns are not silently reinterpreted as authoritative per-chapter ownership.",
    ),
    ServiceDescriptor(
        service_id="achievement.google_sheets.sync",
        domain="achievement",
        purpose="Read and write the external BFF Google Sheets achievement tracker through its historical tab/column layout.",
        implementation_path="services.google_sheets_service",
        inputs=("GoogleSheetCredentials", "SpreadsheetId", "AchievementName", "AchievementProfileSource"),
        outputs=("GoogleSheetAchievementSnapshot", "ExternalAchievementStatus"),
        responsibilities=("google_sheets_achievement_sync",),
        behavior=ServiceBehavior.DETERMINISTIC,
        ui_safe=True,
        evidence_class=EvidenceClass.NONE,
        notes="Google Sheets is an external synchronization surface, not BFF's local completion authority. Missing tabs and unknown achievements remain explicit instead of being guessed or silently treated as complete/incomplete.",
    ),
)


__all__ = ["COLLECTION_SYNC_SERVICE_DESCRIPTORS"]
