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
)


__all__ = ["EXTREME_RECOVERY_SERVICE_DESCRIPTORS"]
