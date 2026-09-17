from __future__ import annotations

"""Search legal named-gear packages for reviewed stealth-radius sources.

This service deliberately stops before projecting a final detection radius.  The
canonical gear resolver expresses Night Terror-style effects as flat metres while
the retained legacy sneak-detect equation exposes a multiplicative set channel.
Until that stacking contract is reviewed, Extreme may rank *reviewed flat source
strength* but must not manufacture a final radius from incompatible units.

Gear legality is not reimplemented here.  The service reuses the canonical Extreme
set topology, breakpoint relevance, named-set slot eligibility, and objective-
specific realization layers.
"""

from dataclasses import dataclass
from pathlib import Path

from minmax.gear_set_repository import GearSetRepository
from services.extreme_gear_set_bonus_breakpoint_service import (
    ExtremeGearSetBonusBreakpointService,
)
from services.extreme_gear_set_objective_relevance_service import (
    ExtremeGearSetObjectiveRelevance,
    ExtremeGearSetObjectiveRelevanceCatalog,
    ExtremeGearSetObjectiveRelevanceService,
)
from services.extreme_gear_set_topology_catalog_service import (
    ExtremeGearSetTopologyCatalogService,
)
from services.extreme_named_gear_set_realization_service import (
    ExtremeNamedGearSetRealization,
)
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibilityService,
)
from services.extreme_objective_named_gear_set_catalog_realization_service import (
    ExtremeObjectiveNamedGearSetCatalogRealizationService,
)


OBJECTIVE_KEY = "detection_radius_reduction"


@dataclass(frozen=True)
class ExtremeStealthSourcePackageResult:
    realization: ExtremeNamedGearSetRealization | None
    reviewed_flat_reduction_meters: float
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]
    gear_denominator_proven: bool

    @property
    def mechanic_complete(self) -> bool:
        return bool(self.realization is not None and not self.unresolved)


class ExtremeStealthSourcePackageService:
    """Return the strongest reviewed legal named-set stealth package."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    @staticmethod
    def _score_realization(
        realization: ExtremeNamedGearSetRealization,
        relevance: ExtremeGearSetObjectiveRelevanceCatalog,
    ) -> tuple[float, tuple[str, ...], tuple[str, ...]]:
        evidence_by_key = {
            (int(row.set_id), int(row.piece_count)): row
            for row in relevance.evidence
        }
        total = 0.0
        evidence: list[str] = []
        unresolved: list[str] = []

        for set_id, piece_count, set_name in zip(
            realization.set_ids,
            realization.counts,
            realization.set_names,
        ):
            row = evidence_by_key.get((int(set_id), int(piece_count)))
            if row is None:
                unresolved.append(
                    f"{set_name} ({piece_count}): no stealth objective evidence"
                )
                continue
            if row.status is ExtremeGearSetObjectiveRelevance.PROVEN_IRRELEVANT:
                continue
            if row.status is ExtremeGearSetObjectiveRelevance.UNRESOLVED:
                unresolved.extend(row.candidate.unresolved or (
                    f"{set_name} ({piece_count}): stealth contribution unresolved",
                ))
                continue
            if row.candidate.unresolved:
                unresolved.extend(row.candidate.unresolved)
                continue
            contribution = float(row.reviewed_delta)
            if contribution > 0.0:
                total += contribution
                evidence.append(
                    f"{set_name} ({piece_count}): {contribution:g} m reviewed detection-radius reduction"
                )

        return (
            total,
            tuple(dict.fromkeys(evidence)),
            tuple(dict.fromkeys(item for item in unresolved if item)),
        )

    def evaluate(self) -> ExtremeStealthSourcePackageResult:
        repository = GearSetRepository(self.database_path)
        topology = ExtremeGearSetTopologyCatalogService(repository).build()
        breakpoints = ExtremeGearSetBonusBreakpointService(repository).build()
        eligibility = ExtremeNamedGearSetSlotEligibilityService(self.database_path).build()
        relevance = ExtremeGearSetObjectiveRelevanceService(repository).build(
            OBJECTIVE_KEY,
            breakpoints,
        )
        realized = ExtremeObjectiveNamedGearSetCatalogRealizationService(
            breakpoints=breakpoints,
            eligibility=eligibility,
            relevance=relevance,
        ).build(topology)

        best: ExtremeNamedGearSetRealization | None = None
        best_value = 0.0
        best_evidence: tuple[str, ...] = ()
        best_unresolved: tuple[str, ...] = ()

        for topology_row in realized.realization.topologies:
            for witness in topology_row.realizations:
                value, evidence_rows, unresolved_rows = self._score_realization(
                    witness,
                    relevance,
                )
                identity = (
                    tuple(witness.set_names),
                    tuple(int(value) for value in witness.counts),
                    witness.weapon_shape.value,
                )
                best_identity = (
                    tuple(best.set_names),
                    tuple(int(value) for value in best.counts),
                    best.weapon_shape.value,
                ) if best is not None else None
                if (
                    best is None
                    or value > best_value + 1e-12
                    or (abs(value - best_value) <= 1e-12 and identity < best_identity)
                ):
                    best = witness
                    best_value = value
                    best_evidence = evidence_rows
                    best_unresolved = unresolved_rows

        unresolved = tuple(
            dict.fromkeys(
                (
                    *relevance.unresolved,
                    *realized.unresolved,
                    *best_unresolved,
                    "Final detection-radius stacking for flat set/racial metre reductions is not yet reviewed",
                    "Khajiit Feline Ambush racial 3 m reduction is canonical but not yet composed into this named-gear package",
                )
            )
        )
        denominator_proven = bool(
            topology.count_topology_denominator_proven
            and eligibility.named_set_slot_eligibility_proven
            and realized.denominator_proven
        )
        return ExtremeStealthSourcePackageResult(
            realization=best,
            reviewed_flat_reduction_meters=float(best_value),
            evidence=best_evidence,
            unresolved=unresolved,
            gear_denominator_proven=denominator_proven,
        )


__all__ = [
    "ExtremeStealthSourcePackageResult",
    "ExtremeStealthSourcePackageService",
]
