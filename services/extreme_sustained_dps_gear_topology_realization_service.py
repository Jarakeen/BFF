from __future__ import annotations

"""On-demand named-set physical realization for sustained-DPS gear topology branches."""

from dataclasses import dataclass

from minmax.gear_set_repository import GearSetRepository
from services.extreme_gear_set_bonus_breakpoint_service import (
    ExtremeGearSetBonusBreakpointService,
)
from services.extreme_named_gear_set_catalog_realization_service import (
    ExtremeNamedGearSetCatalogRealizationService,
    ExtremeNamedGearSetTopologyRealizationResult,
)
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibilityService,
)
from services.extreme_sustained_dps_gear_topology_frontier_service import (
    ExtremeSustainedDPSGearTopologyFrontierService,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSGearTopologyRealization:
    topology_index: int
    topology_signature: str
    assignments_considered: int
    assignments_realized: int
    assignments_rejected: int
    truncated: bool
    denominator_proven: bool
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]
    result: ExtremeNamedGearSetTopologyRealizationResult


class ExtremeSustainedDPSGearTopologyRealizationService:
    """Expand one abstract gear topology into exact named physical witnesses."""

    def __init__(
        self,
        *,
        topology_service: ExtremeSustainedDPSGearTopologyFrontierService,
        realization_service: ExtremeNamedGearSetCatalogRealizationService,
    ) -> None:
        self.topology_service = topology_service
        self.realization_service = realization_service

    @classmethod
    def from_database(cls, database_path) -> "ExtremeSustainedDPSGearTopologyRealizationService":
        repository = GearSetRepository(database_path)
        topology_service = ExtremeSustainedDPSGearTopologyFrontierService(repository)
        breakpoints = ExtremeGearSetBonusBreakpointService(repository).build()
        eligibility = ExtremeNamedGearSetSlotEligibilityService(database_path).build()
        realization_service = ExtremeNamedGearSetCatalogRealizationService(
            breakpoints=breakpoints,
            eligibility=eligibility,
        )
        return cls(
            topology_service=topology_service,
            realization_service=realization_service,
        )

    def realize(
        self,
        topology_index: int,
        *,
        max_assignments: int | None = None,
    ) -> ExtremeSustainedDPSGearTopologyRealization:
        topology = self.topology_service.topology_at(topology_index)
        result = self.realization_service.realize_topology(
            topology,
            max_assignments=max_assignments,
        )

        if not isinstance(result.unresolved, tuple):
            raise TypeError("gear topology realization unresolved evidence must be a tuple")
        if not isinstance(result.truncated, bool):
            raise TypeError("gear topology realization truncated flag must be boolean")
        if not isinstance(result.denominator_proven, bool):
            raise TypeError("gear topology realization denominator proof must be boolean")
        unresolved = list(result.unresolved)
        if result.truncated:
            unresolved.append(
                "Named-set assignment search was truncated; this topology branch is exploratory, not denominator-proven"
            )
        final_unresolved = tuple(dict.fromkeys(item for item in unresolved if item))
        proven = result.denominator_proven and not final_unresolved
        return ExtremeSustainedDPSGearTopologyRealization(
            topology_index=int(topology_index),
            topology_signature=topology.signature,
            assignments_considered=int(result.assignments_considered),
            assignments_realized=int(result.assignments_realized),
            assignments_rejected=int(result.assignments_rejected),
            truncated=result.truncated,
            denominator_proven=proven,
            evidence=(
                f"Topology: {topology.signature}",
                f"Named assignments considered: {result.assignments_considered}",
                f"Physical witnesses realized: {result.assignments_realized}",
                f"Assignments rejected by physical legality: {result.assignments_rejected}",
                (
                    "Topology branch exhaustively proven empty"
                    if proven and result.assignments_realized == 0
                    else (
                        "Topology branch fully realized"
                        if proven
                        else "Topology branch remains unproven or exploratory"
                    )
                ),
            ),
            unresolved=final_unresolved,
            result=result,
        )


__all__ = [
    "ExtremeSustainedDPSGearTopologyRealization",
    "ExtremeSustainedDPSGearTopologyRealizationService",
]
