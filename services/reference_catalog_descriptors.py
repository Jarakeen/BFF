from __future__ import annotations

"""Reference-data and achievement-reference catalog descriptors.

Metadata only. Runtime code continues to use typed imports and explicit wiring.
These descriptors separate live SQLite-backed reference access from older standalone
JSON reference layers that remain only for historical/old-page compatibility.
"""

from services.service_catalog import (
    EvidenceClass,
    ServiceAuthority,
    ServiceBehavior,
    ServiceDescriptor,
)


REFERENCE_SERVICE_DESCRIPTORS: tuple[ServiceDescriptor, ...] = (
    ServiceDescriptor(
        service_id="reference.eso_db.ui_lookup",
        domain="reference",
        purpose="Provide live read-only UI/reference lookups from the populated canonical ESO SQLite database.",
        implementation_path="services.reference_data_service",
        inputs=("EsoDatabase", "GearSetName", "CanonicalSkillRecord"),
        outputs=("ReferenceLookupResult", "WatchSuggestion"),
        responsibilities=("canonical_eso_reference_ui_lookup",),
        behavior=ServiceBehavior.HYBRID,
        ui_safe=True,
        evidence_class=EvidenceClass.MIXED,
        notes="SQLite rows are the live reference source. Major/Minor watch suggestions extracted from set-description text are convenience heuristics and must not be promoted into canonical mechanic truth.",
    ),
    ServiceDescriptor(
        service_id="reference.combat_effect.sqlite",
        domain="reference",
        purpose="Expose read-only canonical combat-effect, trigger, and interaction records for human-readable reference surfaces.",
        implementation_path="services.combat_effect_reference_service",
        inputs=("CanonicalEsoDatabase",),
        outputs=("CombatEffectReference",),
        responsibilities=("canonical_combat_effect_reference_lookup",),
        behavior=ServiceBehavior.DETERMINISTIC,
        ui_safe=True,
        evidence_class=EvidenceClass.GAME_MECHANIC,
        provenance=("combat_effect", "combat_effect_trigger", "combat_effect_interaction"),
        notes="Presentation consumers may explain imported effect rows but must not infer missing durations, triggers, interactions, or gameplay-practice policy.",
    ),
    ServiceDescriptor(
        service_id="reference.legacy_json_library",
        domain="reference",
        purpose="Legacy standalone-JSON reference index retained for old-page compatibility.",
        implementation_path="services.reference_service",
        inputs=("StandaloneReferenceJsonDirectory",),
        outputs=("LegacyReferenceLibrary",),
        authority=ServiceAuthority.DEPRECATED,
        superseded_by="reference.eso_db.ui_lookup",
        responsibilities=("legacy_json_reference_lookup",),
        behavior=ServiceBehavior.DETERMINISTIC,
        evidence_class=EvidenceClass.MIXED,
        notes="Current live pages use SQLite-backed reference access; remaining consumers are historical old_pages code.",
    ),
    ServiceDescriptor(
        service_id="achievement.reference.sqlite",
        domain="achievement",
        purpose="Provide read-only achievement/category/criteria reference access from the imported ESO SQLite corpus.",
        implementation_path="services.eso_achievement_database_service",
        inputs=("CanonicalEsoDatabase", "AchievementId", "AchievementCategory"),
        outputs=("AchievementReference", "AchievementCategoryReference"),
        responsibilities=("canonical_achievement_reference_lookup",),
        behavior=ServiceBehavior.DETERMINISTIC,
        ui_safe=True,
        evidence_class=EvidenceClass.GAME_MECHANIC,
        notes="Read-only imported achievement reference data. User completion/progress state is owned by separate progress services.",
    ),
    ServiceDescriptor(
        service_id="achievement.reference.legacy_json",
        domain="achievement",
        purpose="Legacy parsed-JSON achievement reference reader retained only for the old application window.",
        implementation_path="services.eso_data_service",
        inputs=("EsoAchievementTreeJson", "EsoAchievementsJson"),
        outputs=("LegacyAchievementReference",),
        authority=ServiceAuthority.DEPRECATED,
        superseded_by="achievement.reference.sqlite",
        responsibilities=("legacy_achievement_reference_lookup",),
        behavior=ServiceBehavior.DETERMINISTIC,
        evidence_class=EvidenceClass.GAME_MECHANIC,
        notes="Superseded by SQLite-backed achievement reference access; current repository usage is limited to old_pages.",
    ),
)


__all__ = ["REFERENCE_SERVICE_DESCRIPTORS"]
