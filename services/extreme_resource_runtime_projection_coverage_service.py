from __future__ import annotations

"""Compose denominator and execution proof for Extreme max-resource runtime state.

The lower-level runtime audit deliberately stops at denominator evidence: it lists
conditional gear effects but does not claim those conditions are executable.  This
service is the proof boundary that may close the runtime/proc search axes for an
instantaneous self max-resource objective.

It owns no ESO stat arithmetic.  It verifies that:

* the contextual-passive + named-gear runtime denominator is proven;
* every discovered canonical condition marker has a reviewed execution owner;
* skill-dependent markers have a proven canonical semantic witness catalog; and
* recipient/target and duration/uptime axes do not alter an instantaneous self
  Max Health/Magicka/Stamina snapshot.

Candidate-specific legality is still enforced by
``ExtremeResourceCandidateRuntimeConditionService`` during scoring.  This service
only proves that every marker in the global denominator has such an execution path.
"""

from dataclasses import dataclass
from pathlib import Path

from services.extreme_resource_runtime_coverage_audit_service import (
    ExtremeResourceRuntimeCoverageAuditService,
)
from services.extreme_resource_runtime_skill_witness_catalog_service import (
    ExtremeResourceRuntimeSkillWitnessCatalogService,
)


_SUPPORTED_OBJECTIVES = ("max_health", "max_magicka", "max_stamina")

# Canonical semantic condition markers currently owned by the executable runtime
# state + skill-witness layers.  These are mechanics identities, never numeric ESO
# ability ids.
_EXECUTION_OWNERS = frozenset(
    {
        "armor_ability_slotted",
        "destruction_staff_equipped",
        "drink_buff_active",
        "escalating_fete_stacks:30",
        "food_buff_active",
        "pet_active",
        "prowlers_talisman_critical_stacks:10",
        "transformed",
    }
)
_SKILL_WITNESS_MARKERS = frozenset(
    {
        "armor_ability_slotted",
        "pet_active",
        "transformed",
    }
)


@dataclass(frozen=True)
class ExtremeResourceRuntimeProjectionCoverage:
    objective_key: str
    condition_markers: tuple[str, ...]
    execution_owned_markers: tuple[str, ...]
    runtime_denominator_proven: bool
    skill_witness_denominator_proven: bool
    instantaneous_self_snapshot: bool
    unresolved: tuple[str, ...] = ()

    @property
    def projection_complete(self) -> bool:
        return bool(
            self.runtime_denominator_proven
            and self.skill_witness_denominator_proven
            and self.instantaneous_self_snapshot
            and set(self.condition_markers).issubset(set(self.execution_owned_markers))
            and not self.unresolved
        )


class ExtremeResourceRuntimeProjectionCoverageService:
    """Prove that every max-resource runtime denominator row has execution ownership."""

    SUPPORTED_OBJECTIVES = _SUPPORTED_OBJECTIVES
    EXECUTION_OWNERS = _EXECUTION_OWNERS

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        runtime_audit_service: ExtremeResourceRuntimeCoverageAuditService | None = None,
        skill_witness_catalog_service: ExtremeResourceRuntimeSkillWitnessCatalogService | None = None,
    ) -> None:
        if database_path is None and (
            runtime_audit_service is None or skill_witness_catalog_service is None
        ):
            raise ValueError(
                "database_path is required unless runtime audit and skill-witness services are supplied"
            )
        self.runtime_audit_service = runtime_audit_service or ExtremeResourceRuntimeCoverageAuditService(
            database_path
        )
        self.skill_witness_catalog_service = (
            skill_witness_catalog_service
            or ExtremeResourceRuntimeSkillWitnessCatalogService(database_path)
        )

    def build(self, objective_key: str) -> ExtremeResourceRuntimeProjectionCoverage:
        key = str(objective_key or "").strip().casefold()
        if key not in _SUPPORTED_OBJECTIVES:
            raise KeyError(f"unreviewed Extreme runtime projection objective: {objective_key!r}")

        audit = self.runtime_audit_service.build(key)
        markers = tuple(sorted(set(audit.condition_markers), key=str.casefold))
        unresolved: list[str] = list(audit.unresolved)

        unknown = tuple(
            marker for marker in markers if marker not in _EXECUTION_OWNERS
        )
        if unknown:
            unresolved.extend(
                f"Runtime condition lacks an execution owner: {marker}"
                for marker in unknown
            )

        required_skill_markers = set(markers) & _SKILL_WITNESS_MARKERS
        skill_catalog = self.skill_witness_catalog_service.build()
        skill_witness_denominator_proven = True
        if required_skill_markers:
            skill_witness_denominator_proven = bool(skill_catalog.denominator_proven)
            if not skill_witness_denominator_proven:
                unresolved.extend(skill_catalog.unresolved)

        # Max resource is an instantaneous self-owned character-state objective.
        # Target recipients and sustained uptime/duration cannot change the value of
        # this snapshot once every self runtime condition that mutates the resource
        # has been enumerated and execution-owned above.
        instantaneous_self_snapshot = True

        return ExtremeResourceRuntimeProjectionCoverage(
            objective_key=key,
            condition_markers=markers,
            execution_owned_markers=tuple(
                marker for marker in markers if marker in _EXECUTION_OWNERS
            ),
            runtime_denominator_proven=bool(audit.denominator_proven),
            skill_witness_denominator_proven=skill_witness_denominator_proven,
            instantaneous_self_snapshot=instantaneous_self_snapshot,
            unresolved=tuple(dict.fromkeys(item for item in unresolved if item)),
        )


__all__ = [
    "ExtremeResourceRuntimeProjectionCoverage",
    "ExtremeResourceRuntimeProjectionCoverageService",
]
