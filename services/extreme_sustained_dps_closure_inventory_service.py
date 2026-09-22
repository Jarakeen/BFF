from __future__ import annotations

"""Objective #32 closure inventory.

This module does not decide combat math. It composes already-reviewed runtime-effect
relevance blockers with shared canonical mechanics coverage so remaining closure work
is separated into source-data acquisition, math/review work, and broader mechanics
evidence.
"""

from dataclasses import dataclass

from services.canonical_knowledge_gap import CanonicalKnowledgeGap
from services.canonical_mechanics_coverage_audit import (
    CanonicalMechanicsCoverageAuditService,
)
from services.canonical_mechanics_coverage_inventory import (
    shared_canonical_mechanics_inventory,
)
from services.extreme_sustained_dps_runtime_effect_relevance_service import (
    ExtremeSustainedDPSRuntimeEffectRelevance,
)


OBJECTIVE32_MECHANICS_DEPENDENCIES = (
    "effect_duration:build_modifiers",
    "heavy_attack:restoration",
    "passives:runtime_semantics",
    "armor:weight_passive_semantics",
    "gear:conditional_topology",
    "skills:runtime_topology",
    "procs:conditional_topology",
    "consumables:runtime_resource_and_buff_policy",
    "consumables:potion_cooldown_effective",
    "weapon_enchantments:runtime_cadence",
    "weapons:bash_interrupt_poison_topology",
    "encounter:target_range_movement_topology",
)


@dataclass(frozen=True)
class ExtremeSustainedDPSClosureInventory:
    source_data_blockers: tuple[str, ...]
    math_review_blockers: tuple[str, ...]
    mechanics_blockers: tuple[CanonicalKnowledgeGap, ...]
    mechanics_advisories: tuple[CanonicalKnowledgeGap, ...]
    evidence: tuple[str, ...]

    @property
    def blocking_count(self) -> int:
        return (
            len(self.source_data_blockers)
            + len(self.math_review_blockers)
            + len(self.mechanics_blockers)
        )

    @property
    def closure_ready(self) -> bool:
        return self.blocking_count == 0


class ExtremeSustainedDPSClosureInventoryService:
    """Compose actionable Objective #32 closure blockers without weakening gates."""

    @classmethod
    def build(
        cls,
        *,
        relevance: ExtremeSustainedDPSRuntimeEffectRelevance | None = None,
        mechanics_dependency_keys: tuple[str, ...] = OBJECTIVE32_MECHANICS_DEPENDENCIES,
    ) -> ExtremeSustainedDPSClosureInventory:
        report = CanonicalMechanicsCoverageAuditService().audit(
            shared_canonical_mechanics_inventory()
        )
        mechanics = report.dependency_gaps_for(
            "optimizer",
            tuple(mechanics_dependency_keys),
        )
        blocking_mechanics = tuple(gap for gap in mechanics if gap.blocking)
        advisory_mechanics = tuple(gap for gap in mechanics if not gap.blocking)

        source_data = (
            tuple(relevance.source_data_unresolved)
            if relevance is not None
            else ()
        )
        math_review = (
            tuple(relevance.math_unresolved)
            if relevance is not None
            else ()
        )

        return ExtremeSustainedDPSClosureInventory(
            source_data_blockers=tuple(dict.fromkeys(source_data)),
            math_review_blockers=tuple(dict.fromkeys(math_review)),
            mechanics_blockers=blocking_mechanics,
            mechanics_advisories=advisory_mechanics,
            evidence=(
                f"Objective #32 source-data blockers: {len(tuple(dict.fromkeys(source_data)))}",
                f"Objective #32 math/review blockers: {len(tuple(dict.fromkeys(math_review)))}",
                f"Objective #32 blocking mechanics gaps: {len(blocking_mechanics)}",
                f"Objective #32 advisory mechanics gaps: {len(advisory_mechanics)}",
                (
                    "Objective #32 closure inventory is blocker-free"
                    if not source_data and not math_review and not blocking_mechanics
                    else "Objective #32 closure inventory remains open"
                ),
            ),
        )


__all__ = [
    "OBJECTIVE32_MECHANICS_DEPENDENCIES",
    "ExtremeSustainedDPSClosureInventory",
    "ExtremeSustainedDPSClosureInventoryService",
]
