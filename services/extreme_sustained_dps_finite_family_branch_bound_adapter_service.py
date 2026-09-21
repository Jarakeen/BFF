from __future__ import annotations

"""Safely adapt finite-family dominance ceilings into branch-and-bound evidence."""

from dataclasses import dataclass

from services.extreme_sustained_dps_finite_whole_plan_dominance_service import (
    ExtremeSustainedDPSFiniteWholePlanDominanceResult,
)
from services.extreme_sustained_dps_pruning_service import (
    ExtremeSustainedDPSBoundEvidence,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSFiniteFamilyBranchScopeProof:
    branch_candidate_key: str
    family_candidate_key: str
    denominator_matches_branch: bool
    excluded_omitted_scope: tuple[str, ...] = ()
    source: str = "caller-supplied finite-family branch-scope proof"

    def __post_init__(self) -> None:
        branch_key = str(self.branch_candidate_key or "").strip()
        family_key = str(self.family_candidate_key or "").strip()
        if not branch_key:
            raise ValueError("finite-family branch scope requires branch_candidate_key")
        if not family_key:
            raise ValueError("finite-family branch scope requires family_candidate_key")
        object.__setattr__(self, "branch_candidate_key", branch_key)
        object.__setattr__(self, "family_candidate_key", family_key)
        object.__setattr__(
            self,
            "excluded_omitted_scope",
            tuple(
                dict.fromkeys(
                    str(item).strip()
                    for item in self.excluded_omitted_scope
                    if str(item).strip()
                )
            ),
        )
        object.__setattr__(
            self,
            "source",
            str(self.source or "").strip()
            or "caller-supplied finite-family branch-scope proof",
        )


@dataclass(frozen=True)
class ExtremeSustainedDPSFiniteFamilyBranchBoundAdaptation:
    bound: ExtremeSustainedDPSBoundEvidence
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]


class ExtremeSustainedDPSFiniteFamilyBranchBoundAdapterService:
    """Require exact branch-scope proof before promoting a local family ceiling."""

    @classmethod
    def adapt(
        cls,
        result: ExtremeSustainedDPSFiniteWholePlanDominanceResult,
        *,
        scope: ExtremeSustainedDPSFiniteFamilyBranchScopeProof,
    ) -> ExtremeSustainedDPSFiniteFamilyBranchBoundAdaptation:
        unresolved: list[str] = []

        if result.candidate_key != scope.family_candidate_key:
            unresolved.append(
                "Finite-family result identity does not match branch-scope family identity"
            )
        if not scope.denominator_matches_branch:
            unresolved.append(
                "Finite-family denominator is not proven identical to the branch denominator"
            )

        omitted = tuple(
            dict.fromkeys(
                str(item).strip()
                for item in result.omitted_scope
                if str(item).strip()
            )
        )
        excluded = set(scope.excluded_omitted_scope)
        missing_exclusions = tuple(
            item
            for item in omitted
            if item not in excluded
        )
        if missing_exclusions:
            unresolved.append(
                "Finite-family omitted scope is not explicitly excluded from the branch: "
                + "; ".join(missing_exclusions)
            )

        if not result.bound.proven_safe or result.bound.upper_bound_dps is None:
            unresolved.extend(
                str(item).strip()
                for item in result.bound.unresolved
                if str(item).strip()
            )
            if not result.bound.unresolved:
                unresolved.append(
                    "Finite-family dominance result does not carry a proven-safe numeric ceiling"
                )

        deduped = tuple(
            dict.fromkeys(
                str(item).strip()
                for item in unresolved
                if str(item).strip()
            )
        )
        safe = not deduped

        bound = ExtremeSustainedDPSBoundEvidence(
            candidate_key=scope.branch_candidate_key,
            upper_bound_dps=(
                float(result.bound.upper_bound_dps)
                if safe and result.bound.upper_bound_dps is not None
                else None
            ),
            proven_safe=safe,
            source=(
                "finite-family branch-bound adaptation; "
                + scope.source
                if safe
                else "finite-family branch-bound adaptation withheld"
            ),
            unresolved=deduped,
        )

        return ExtremeSustainedDPSFiniteFamilyBranchBoundAdaptation(
            bound=bound,
            evidence=(
                f"Branch candidate: {scope.branch_candidate_key}",
                f"Finite family candidate: {scope.family_candidate_key}",
                f"Finite denominator equals branch denominator: {bool(scope.denominator_matches_branch)}",
                f"Finite-family omitted scope items: {len(omitted)}",
                f"Explicitly excluded omitted scope items: {len(scope.excluded_omitted_scope)}",
                (
                    f"Promoted branch ceiling: {bound.upper_bound_dps:g}"
                    if bound.upper_bound_dps is not None
                    else "Promoted branch ceiling: withheld"
                ),
                "Local finite-family closure is never promoted to a wider branch without exact scope proof",
            ),
            unresolved=deduped,
        )


__all__ = [
    "ExtremeSustainedDPSFiniteFamilyBranchBoundAdaptation",
    "ExtremeSustainedDPSFiniteFamilyBranchBoundAdapterService",
    "ExtremeSustainedDPSFiniteFamilyBranchScopeProof",
]
