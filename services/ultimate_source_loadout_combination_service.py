from __future__ import annotations

"""Search exact equipment combinations for reviewed Ultimate-source candidates.

This service is denominator legality only. It combines finite Ultimate-source
candidates, proves exact named-set coexistence through the canonical named-set
realization service, and preserves stochastic/action-proof caveats. It does not
prove armor-weight compatibility or whole-build Health Recovery scoring.
"""

from dataclasses import dataclass
from itertools import combinations

from services.extreme_gear_set_topology_catalog_service import (
    ACTIVE_SNAPSHOT_SET_UNITS,
    ExtremeGearSetCountTopology,
)
from services.extreme_named_gear_set_realization_service import (
    ExtremeNamedGearSetRealization,
    ExtremeNamedGearSetRealizationService,
)
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibility,
)


@dataclass(frozen=True)
class UltimateSourceLoadoutCandidate:
    source_id: str
    label: str
    generated_ultimate_ceiling: float
    required_set_name: str | None = None
    required_set_pieces: int = 0
    stochastic: bool = False
    action_proof_required: bool = False

    def __post_init__(self) -> None:
        source_id = str(self.source_id or "").strip()
        label = str(self.label or "").strip()
        required_set_name = (
            str(self.required_set_name).strip()
            if self.required_set_name is not None
            else None
        )
        if not source_id:
            raise ValueError("source_id is required")
        if not label:
            raise ValueError("label is required")
        if float(self.generated_ultimate_ceiling) < 0:
            raise ValueError("generated_ultimate_ceiling must be non-negative")
        if int(self.required_set_pieces) < 0:
            raise ValueError("required_set_pieces must be non-negative")
        if bool(required_set_name) != (int(self.required_set_pieces) > 0):
            raise ValueError(
                "required_set_name and positive required_set_pieces must be supplied together"
            )
        object.__setattr__(self, "source_id", source_id)
        object.__setattr__(self, "label", label)
        object.__setattr__(self, "required_set_name", required_set_name)
        object.__setattr__(
            self,
            "generated_ultimate_ceiling",
            float(self.generated_ultimate_ceiling),
        )
        object.__setattr__(self, "required_set_pieces", int(self.required_set_pieces))


@dataclass(frozen=True)
class UltimateSourceLoadoutCombination:
    source_ids: tuple[str, ...]
    total_ultimate_ceiling: float
    required_set_names: tuple[str, ...]
    required_set_units: int
    physically_legal: bool
    closes_gap: bool
    stochastic: bool
    action_proof_required: bool
    runtime_proven: bool
    witness: ExtremeNamedGearSetRealization | None = None
    rejection_reason: str = ""


@dataclass(frozen=True)
class UltimateSourceLoadoutCombinationCatalog:
    candidates: tuple[UltimateSourceLoadoutCandidate, ...]
    combinations: tuple[UltimateSourceLoadoutCombination, ...]
    required_ultimate_gap: float
    physical_set_slot_denominator_proven: bool
    unresolved: tuple[str, ...] = ()

    @property
    def legal_combinations(self) -> tuple[UltimateSourceLoadoutCombination, ...]:
        return tuple(row for row in self.combinations if row.physically_legal)

    @property
    def rejected_combinations(self) -> tuple[UltimateSourceLoadoutCombination, ...]:
        return tuple(row for row in self.combinations if not row.physically_legal)

    @property
    def gap_closing_combinations(self) -> tuple[UltimateSourceLoadoutCombination, ...]:
        return tuple(
            row
            for row in self.combinations
            if row.physically_legal and row.closes_gap
        )

    @property
    def minimal_gap_closing_combinations(
        self,
    ) -> tuple[UltimateSourceLoadoutCombination, ...]:
        closers = self.gap_closing_combinations
        output: list[UltimateSourceLoadoutCombination] = []
        for row in closers:
            row_ids = frozenset(row.source_ids)
            if any(
                frozenset(other.source_ids) < row_ids
                for other in closers
            ):
                continue
            output.append(row)
        return tuple(output)


class UltimateSourceLoadoutCombinationService:
    """Enumerate and prove exact finite loadout combinations."""

    @staticmethod
    def _eligibility_index(
        named_sets: tuple[ExtremeNamedGearSetSlotEligibility, ...],
    ) -> tuple[
        dict[str, ExtremeNamedGearSetSlotEligibility],
        tuple[str, ...],
    ]:
        rows_by_name: dict[str, list[ExtremeNamedGearSetSlotEligibility]] = {}
        for row in named_sets:
            key = row.name.strip().casefold()
            if key:
                rows_by_name.setdefault(key, []).append(row)

        resolved: dict[str, ExtremeNamedGearSetSlotEligibility] = {}
        unresolved: list[str] = []
        for key, rows in rows_by_name.items():
            if len(rows) == 1:
                resolved[key] = rows[0]
            else:
                unresolved.append(
                    f"Named set {rows[0].name!r} has multiple eligibility rows"
                )
        return resolved, tuple(unresolved)

    @staticmethod
    def _named_requirements(
        subset: tuple[UltimateSourceLoadoutCandidate, ...],
        eligibility_by_name: dict[str, ExtremeNamedGearSetSlotEligibility],
    ) -> tuple[
        tuple[tuple[int, ExtremeNamedGearSetSlotEligibility], ...],
        tuple[str, ...],
    ]:
        requirements: list[tuple[int, ExtremeNamedGearSetSlotEligibility]] = []
        unresolved: list[str] = []
        seen_set_ids: set[int] = set()

        for candidate in subset:
            if candidate.required_set_name is None:
                continue
            eligibility = eligibility_by_name.get(
                candidate.required_set_name.casefold()
            )
            if eligibility is None:
                unresolved.append(
                    f"{candidate.source_id}: no exact named-set eligibility for "
                    f"{candidate.required_set_name!r}"
                )
                continue
            if not eligibility.has_physical_slot_evidence:
                unresolved.append(
                    f"{candidate.source_id}: named set {eligibility.name!r} has no "
                    "physical slot evidence"
                )
                continue
            if candidate.required_set_pieces > eligibility.max_equip_count:
                unresolved.append(
                    f"{candidate.source_id}: requires {candidate.required_set_pieces} "
                    f"pieces of {eligibility.name!r}, above canonical max "
                    f"{eligibility.max_equip_count}"
                )
                continue
            if eligibility.set_id in seen_set_ids:
                unresolved.append(
                    f"{candidate.source_id}: duplicate named-set identity "
                    f"{eligibility.name!r} in one source combination"
                )
                continue
            seen_set_ids.add(eligibility.set_id)
            requirements.append((candidate.required_set_pieces, eligibility))

        requirements.sort(
            key=lambda item: (
                -item[0],
                item[1].name.casefold(),
                item[1].set_id,
            )
        )
        return tuple(requirements), tuple(unresolved)

    @classmethod
    def search(
        cls,
        candidates: tuple[UltimateSourceLoadoutCandidate, ...],
        named_sets: tuple[ExtremeNamedGearSetSlotEligibility, ...],
        *,
        required_ultimate_gap: float,
        active_snapshot_units: int = ACTIVE_SNAPSHOT_SET_UNITS,
    ) -> UltimateSourceLoadoutCombinationCatalog:
        required_gap = float(required_ultimate_gap)
        if required_gap < 0:
            raise ValueError("required_ultimate_gap must be non-negative")
        if int(active_snapshot_units) <= 0:
            raise ValueError("active_snapshot_units must be positive")

        ordered_candidates = tuple(
            sorted(candidates, key=lambda item: item.source_id)
        )
        source_ids = tuple(item.source_id for item in ordered_candidates)
        if len(set(source_ids)) != len(source_ids):
            raise ValueError("candidate source_id values must be unique")

        eligibility_by_name, index_unresolved = cls._eligibility_index(named_sets)
        globally_required_names = tuple(
            dict.fromkeys(
                item.required_set_name
                for item in ordered_candidates
                if item.required_set_name is not None
            )
        )
        unresolved = list(index_unresolved)
        for name in globally_required_names:
            row = eligibility_by_name.get(name.casefold())
            if row is None:
                unresolved.append(f"No exact named-set eligibility for {name!r}")
            elif not row.has_physical_slot_evidence:
                unresolved.append(
                    f"Named set {name!r} has no physical slot evidence"
                )

        output: list[UltimateSourceLoadoutCombination] = []
        for size in range(1, len(ordered_candidates) + 1):
            for subset in combinations(ordered_candidates, size):
                subset_ids = tuple(item.source_id for item in subset)
                total_ceiling = sum(
                    item.generated_ultimate_ceiling for item in subset
                )
                stochastic = any(item.stochastic for item in subset)
                action_proof_required = any(
                    item.action_proof_required for item in subset
                )
                requirements, requirement_unresolved = cls._named_requirements(
                    subset,
                    eligibility_by_name,
                )
                set_names = tuple(row.name for _, row in requirements)
                set_units = sum(count for count, _ in requirements)
                closes_gap = total_ceiling >= required_gap

                witness: ExtremeNamedGearSetRealization | None = None
                physically_legal = False
                rejection_reason = ""

                if requirement_unresolved:
                    rejection_reason = "; ".join(requirement_unresolved)
                elif set_units > int(active_snapshot_units):
                    rejection_reason = (
                        f"named-set requirements use {set_units} active set-count units; "
                        f"canonical snapshot limit is {int(active_snapshot_units)}"
                    )
                elif not requirements:
                    physically_legal = True
                else:
                    topology = ExtremeGearSetCountTopology(
                        counts=tuple(count for count, _ in requirements),
                        unused_units=int(active_snapshot_units) - set_units,
                        total_units=int(active_snapshot_units),
                    )
                    named_rows = tuple(row for _, row in requirements)
                    witness = ExtremeNamedGearSetRealizationService.find_witness(
                        topology,
                        named_rows,
                    )
                    physically_legal = witness is not None
                    if not physically_legal:
                        rejection_reason = (
                            "exact named-set physical realization returned no witness"
                        )

                output.append(
                    UltimateSourceLoadoutCombination(
                        source_ids=subset_ids,
                        total_ultimate_ceiling=total_ceiling,
                        required_set_names=set_names,
                        required_set_units=set_units,
                        physically_legal=physically_legal,
                        closes_gap=closes_gap,
                        stochastic=stochastic,
                        action_proof_required=action_proof_required,
                        runtime_proven=(
                            physically_legal
                            and not stochastic
                            and not action_proof_required
                        ),
                        witness=witness,
                        rejection_reason=rejection_reason,
                    )
                )

        output.sort(key=lambda row: (len(row.source_ids), row.source_ids))
        return UltimateSourceLoadoutCombinationCatalog(
            candidates=ordered_candidates,
            combinations=tuple(output),
            required_ultimate_gap=required_gap,
            physical_set_slot_denominator_proven=not unresolved,
            unresolved=tuple(dict.fromkeys(unresolved)),
        )
