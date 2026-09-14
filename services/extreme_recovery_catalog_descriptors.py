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
)


__all__ = ["EXTREME_RECOVERY_SERVICE_DESCRIPTORS"]
