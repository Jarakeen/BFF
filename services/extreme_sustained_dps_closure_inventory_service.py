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
from services.extreme_sustained_dps_runtime_effect_scaling_service import (
    ExtremeSustainedDPSRuntimeEffectScalingResult,
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

    def __post_init__(self) -> None:
        for name in (
            "source_data_blockers",
            "math_review_blockers",
            "mechanics_blockers",
            "mechanics_advisories",
            "evidence",
        ):
            if not isinstance(getattr(self, name), tuple):
                raise TypeError(f"closure inventory {name} must be a tuple")

        def _strings(values: tuple[str, ...]) -> tuple[str, ...]:
            return tuple(
                dict.fromkeys(
                    str(item).strip()
                    for item in values
                    if str(item).strip()
                )
            )

        if any(not isinstance(row, CanonicalKnowledgeGap) for row in self.mechanics_blockers):
            raise TypeError("closure inventory mechanics_blockers must contain CanonicalKnowledgeGap records")
        if any(not isinstance(row, CanonicalKnowledgeGap) for row in self.mechanics_advisories):
            raise TypeError("closure inventory mechanics_advisories must contain CanonicalKnowledgeGap records")
        overlap = set(self.mechanics_blockers).intersection(self.mechanics_advisories)
        if overlap:
            raise ValueError("closure inventory mechanics gap cannot be both blocker and advisory")

        object.__setattr__(self, "source_data_blockers", _strings(self.source_data_blockers))
        object.__setattr__(self, "math_review_blockers", _strings(self.math_review_blockers))
        object.__setattr__(self, "mechanics_blockers", tuple(self.mechanics_blockers))
        object.__setattr__(self, "mechanics_advisories", tuple(self.mechanics_advisories))
        object.__setattr__(self, "evidence", _strings(self.evidence))

    @property
    def blocking_count(self) -> int:
        return (
            len(self.source_data_blockers)
            + len(self.math_review_blockers)
            + len(self.mechanics_blockers)
        )

    @property
    def closure_ready(self) -> bool:
        return self.blocking_count == 0 and not self.mechanics_advisories


class ExtremeSustainedDPSClosureInventoryService:
    """Compose actionable Objective #32 closure blockers without weakening gates."""

    @classmethod
    def build(
        cls,
        *,
        relevance: ExtremeSustainedDPSRuntimeEffectRelevance | None = None,
        scaling: ExtremeSustainedDPSRuntimeEffectScalingResult | None = None,
        mechanics_dependency_keys: tuple[str, ...] = OBJECTIVE32_MECHANICS_DEPENDENCIES,
    ) -> ExtremeSustainedDPSClosureInventory:
        if relevance is not None and not isinstance(relevance, ExtremeSustainedDPSRuntimeEffectRelevance):
            raise TypeError("Objective #32 closure relevance must be canonical when supplied")
        if scaling is not None and not isinstance(scaling, ExtremeSustainedDPSRuntimeEffectScalingResult):
            raise TypeError("Objective #32 closure scaling must be canonical when supplied")
        if not isinstance(mechanics_dependency_keys, tuple):
            raise TypeError("Objective #32 mechanics_dependency_keys must be a tuple")

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
            *(
                tuple(relevance.source_data_unresolved)
                if relevance is not None
                else ()
            ),
            *(
                tuple(scaling.source_data_unresolved)
                if scaling is not None
                else ()
            ),
        )
        math_review = (
            *(
                tuple(relevance.math_unresolved)
                if relevance is not None
                else ()
            ),
            *(
                tuple(scaling.math_unresolved)
                if scaling is not None
                else ()
            ),
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
                    "Objective #32 closure inventory is fully closed"
                    if (
                        not source_data
                        and not math_review
                        and not blocking_mechanics
                        and not advisory_mechanics
                    )
                    else "Objective #32 closure inventory remains open"
                ),
            ),
        )


__all__ = [
    "OBJECTIVE32_MECHANICS_DEPENDENCIES",
    "ExtremeSustainedDPSClosureInventory",
    "ExtremeSustainedDPSClosureInventoryService",
]
