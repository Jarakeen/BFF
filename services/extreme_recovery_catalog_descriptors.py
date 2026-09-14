from __future__ import annotations

"""Service-catalog descriptors for shared Extreme Recovery mechanics."""

from services.service_catalog import EvidenceClass, ServiceBehavior, ServiceDescriptor


EXTREME_RECOVERY_SERVICE_DESCRIPTORS: tuple[ServiceDescriptor, ...] = (
    ServiceDescriptor(
        service_id="extreme.recovery_passive_special_branch",
        domain="extreme",
        purpose=(
            "Classify non-static Health, Magicka, and Stamina Recovery passive tooltips "
            "without inventing slot, Ultimate, resource, or runtime ceilings."
        ),
        implementation_path="services.extreme_recovery_passive_special_branch_service",
        inputs=("ExtremePlayerSkillRecord", "RecoveryObjective"),
        outputs=("ExtremeRecoveryPassiveBranch",),
        responsibilities=("extreme_recovery_passive_semantic_classification",),
        behavior=ServiceBehavior.DETERMINISTIC,
        evidence_class=EvidenceClass.GAME_MECHANIC,
        notes=(
            "Semantic classification is separate from route scoring. Scaling branches "
            "remain external-ceiling requirements until the appropriate canonical owner proves the maximum."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.recovery_class_route_frontier",
        domain="extreme",
        purpose=(
            "Compose reviewed static class passives, active-bar slot-count Recovery mechanics, "
            "and pure-class Mastery effects across every legal class/subclass line configuration."
        ),
        implementation_path="services.extreme_recovery_class_route_frontier_service",
        inputs=("CanonicalEsoDatabase", "RecoveryObjective", "RecoveryReferenceValue"),
        outputs=("ExtremeRecoveryClassRouteFrontier",),
        dependencies=("extreme.recovery_passive_special_branch",),
        responsibilities=("extreme_recovery_class_route_frontier_projection",),
        behavior=ServiceBehavior.DETERMINISTIC,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Runtime-dependent passives remain explicit obligations. The service does not "
            "convert semantic classification into free score or declare a whole-build record."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.recovery_jewelry_projection",
        domain="extreme",
        purpose=(
            "Project canonical Health, Magicka, or Stamina Recovery jewelry glyphs through "
            "reviewed Gold Infused enchantment scaling without choosing the whole build."
        ),
        implementation_path="services.extreme_recovery_jewelry_projection_service",
        inputs=("JewelryGlyphEffectRepository", "JewelryTraitRepository", "RecoveryObjective"),
        outputs=("ExtremeRecoveryJewelryProjection",),
        responsibilities=("extreme_recovery_jewelry_trait_projection",),
        behavior=ServiceBehavior.DETERMINISTIC,
        evidence_class=EvidenceClass.GAME_MECHANIC,
        notes=(
            "The projection proves glyph and Infused arithmetic only. Whole-build opportunity cost "
            "against alternate jewelry traits remains a higher-level optimization concern."
        ),
    ),
    ServiceDescriptor(
        service_id="extreme.recovery_champion_point_branch",
        domain="extreme",
        purpose=(
            "Classify dynamic or conditional Champion Point branches for Health, Magicka, "
            "and Stamina Recovery while preserving their runtime conditions."
        ),
        implementation_path="services.extreme_recovery_champion_point_branch_service",
        inputs=("ChampionPointRecord", "RecoveryObjective"),
        outputs=("ExtremeRecoveryChampionPointBranch",),
        responsibilities=("extreme_recovery_champion_point_branch_classification",),
        behavior=ServiceBehavior.DETERMINISTIC,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "This service bounds one star only. Four-slot discipline legality remains owned by "
            "ChampionPointLoadoutService, and runtime conditions are not proven by selection."
        ),
    ),
)


__all__ = ["EXTREME_RECOVERY_SERVICE_DESCRIPTORS"]
