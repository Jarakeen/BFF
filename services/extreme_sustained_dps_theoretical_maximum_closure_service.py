from __future__ import annotations

"""Proof gate for the theoretical Extreme MOST Sustained DPS objective."""

from dataclasses import dataclass

from services.extreme_sustained_dps_axis_dominance_composition_service import (
    CANONICAL_SUSTAINED_DPS_MUTATION_AXES,
    ExtremeSustainedDPSAxisDominanceComposition,
)
from services.extreme_sustained_dps_generated_branch_and_bound_search_service import (
    ExtremeSustainedDPSGeneratedSearchResult,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSTheoreticalMaximumClosure:
    finite_denominator_maximum_proven: bool
    canonical_axis_coverage_complete: bool
    mechanics_closure_complete: bool
    omitted_scope: tuple[str, ...]
    theoretical_maximum_proven: bool
    best_modeled_dps: float | None
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]


class ExtremeSustainedDPSTheoreticalMaximumClosureService:
    """Separate finite-tree completion from theoretical objective closure."""

    @classmethod
    def close(
        cls,
        search_result: ExtremeSustainedDPSGeneratedSearchResult,
        *,
        axis_coverage: ExtremeSustainedDPSAxisDominanceComposition,
        omitted_scope: tuple[str, ...] = (),
        closure_inventory: object | None = None,
    ) -> ExtremeSustainedDPSTheoreticalMaximumClosure:
        canonical = tuple(CANONICAL_SUSTAINED_DPS_MUTATION_AXES)
        required = tuple(axis_coverage.required_axes)
        missing_required = tuple(axis for axis in canonical if axis not in required)
        extra_required = tuple(axis for axis in required if axis not in canonical)

        coverage_complete = bool(
            not missing_required
            and not extra_required
            and not axis_coverage.missing_axes
            and not axis_coverage.unresolved
            and axis_coverage.proof.complete
        )

        omitted = tuple(
            dict.fromkeys(
                str(item).strip()
                for item in (
                    *axis_coverage.omitted_scope,
                    *tuple(omitted_scope),
                )
                if str(item).strip()
            )
        )
        mechanics_complete = bool(
            closure_inventory is None
            or bool(getattr(closure_inventory, "closure_ready", False))
        )
        unresolved: list[str] = []

        if not search_result.global_maximum_proven:
            unresolved.append(
                "Generated branch-and-bound did not prove the maximum over its finite search denominator"
            )
        if missing_required:
            unresolved.append(
                "Theoretical closure did not require every canonical sustained-DPS axis: "
                + ", ".join(missing_required)
            )
        if extra_required:
            unresolved.append(
                "Theoretical closure received non-canonical required axes: "
                + ", ".join(extra_required)
            )
        unresolved.extend(
            f"Axis coverage: {item}"
            for item in axis_coverage.unresolved
        )
        if axis_coverage.missing_axes:
            unresolved.append(
                "Canonical sustained-DPS axes remain uncovered: "
                + ", ".join(axis_coverage.missing_axes)
            )
        if omitted:
            unresolved.append(
                "Theoretical sustained-DPS scope remains explicitly omitted: "
                + "; ".join(omitted)
            )
        if closure_inventory is not None and not mechanics_complete:
            source_data = tuple(
                getattr(closure_inventory, "source_data_blockers", ()) or ()
            )
            math_review = tuple(
                getattr(closure_inventory, "math_review_blockers", ()) or ()
            )
            mechanics_blockers = tuple(
                getattr(closure_inventory, "mechanics_blockers", ()) or ()
            )
            mechanics_advisories = tuple(
                getattr(closure_inventory, "mechanics_advisories", ()) or ()
            )
            unresolved.append(
                "Objective #32 mechanics closure remains open: "
                f"source-data={len(source_data)}, "
                f"math/review={len(math_review)}, "
                f"blocking mechanics={len(mechanics_blockers)}, "
                f"partial mechanics={len(mechanics_advisories)}"
            )

        deduped = tuple(dict.fromkeys(unresolved))
        theoretical = bool(
            search_result.global_maximum_proven
            and coverage_complete
            and mechanics_complete
            and not omitted
            and not deduped
        )

        return ExtremeSustainedDPSTheoreticalMaximumClosure(
            finite_denominator_maximum_proven=bool(
                search_result.global_maximum_proven
            ),
            canonical_axis_coverage_complete=coverage_complete,
            mechanics_closure_complete=mechanics_complete,
            omitted_scope=omitted,
            theoretical_maximum_proven=theoretical,
            best_modeled_dps=(
                None
                if search_result.best_modeled_dps is None
                else float(search_result.best_modeled_dps)
            ),
            evidence=(
                f"Finite generated denominator maximum proven: {bool(search_result.global_maximum_proven)}",
                f"Canonical sustained-DPS axes required: {len(canonical)}",
                f"Canonical sustained-DPS axis coverage complete: {coverage_complete}",
                f"Objective #32 mechanics closure complete: {mechanics_complete}",
                f"Explicit omitted theoretical scope items: {len(omitted)}",
                f"Theoretical MOST Sustained DPS maximum proven: {theoretical}",
                "Finite branch-and-bound completion and theoretical objective closure are separate proof claims",
            ),
            unresolved=deduped,
        )


__all__ = [
    "ExtremeSustainedDPSTheoreticalMaximumClosure",
    "ExtremeSustainedDPSTheoreticalMaximumClosureService",
]
