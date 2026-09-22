from __future__ import annotations

"""Promote one completed generated tree into same-tree canonical axis coverage."""

from dataclasses import dataclass

from services.extreme_sustained_dps_axis_dominance_composition_service import (
    ExtremeSustainedDPSAxisCoverageProof,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSGeneratedTreeCoverageResult:
    proof: ExtremeSustainedDPSAxisCoverageProof
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]


class ExtremeSustainedDPSGeneratedTreeCoverageService:
    """Derive coverage only from a successfully exhausted generated search tree."""

    @classmethod
    def from_search(
        cls,
        *,
        search_result: object,
        axis_inventory: object,
    ) -> ExtremeSustainedDPSGeneratedTreeCoverageResult:
        unresolved: list[str] = []

        finite_closed = bool(
            getattr(search_result, "global_maximum_proven", False)
        )
        if not finite_closed:
            unresolved.append(
                "Generated finite search denominator maximum is not proven"
            )

        inventory_unresolved = tuple(
            getattr(axis_inventory, "unresolved", ()) or ()
        )
        unresolved.extend(str(item) for item in inventory_unresolved if str(item))

        duplicates = tuple(
            getattr(axis_inventory, "duplicate_canonical_axes", ()) or ()
        )
        if duplicates:
            unresolved.append(
                "Generated tree contains duplicate canonical-axis enumeration: "
                + ", ".join(str(item) for item in duplicates)
            )

        complete = bool(finite_closed and not unresolved)
        searched_axes = tuple(
            getattr(axis_inventory, "searched_canonical_axes", ()) or ()
        )
        omitted_scope = tuple(
            getattr(axis_inventory, "omitted_scope", ()) or ()
        )

        proof = ExtremeSustainedDPSAxisCoverageProof(
            source="completed generated search tree canonical-axis inventory",
            dominated_axes=searched_axes if complete else (),
            unresolved=tuple(dict.fromkeys(unresolved)),
            omitted_scope=omitted_scope,
        )

        return ExtremeSustainedDPSGeneratedTreeCoverageResult(
            proof=proof,
            evidence=(
                f"Finite generated denominator maximum proven: {finite_closed}",
                f"Canonical axes physically searched: {len(searched_axes)}",
                f"Canonical axes promoted from this exact tree: {len(proof.dominated_axes)}",
                f"Explicit theoretical omissions preserved from tree axes: {len(omitted_scope)}",
                "Coverage promotion uses the same completed generated tree that produced the modeled-DPS winner",
            ),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )


__all__ = [
    "ExtremeSustainedDPSGeneratedTreeCoverageResult",
    "ExtremeSustainedDPSGeneratedTreeCoverageService",
]
