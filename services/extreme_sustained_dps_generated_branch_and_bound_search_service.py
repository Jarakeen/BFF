from __future__ import annotations

"""Proof-safe branch-and-bound coordinator for generated sustained-DPS search.

This service owns search order, incumbent maintenance, exact-leaf accounting, tie
handling, and global-proof bookkeeping only. It never calculates ESO damage and never
manufactures an optimistic bound. Branch expansion and exact leaf evaluation remain
caller-supplied canonical authorities.
"""

from dataclasses import dataclass
import math
from typing import Callable, Protocol

from services.extreme_sustained_dps_pruning_service import (
    ExtremeSustainedDPSBoundEvidence,
    ExtremeSustainedDPSPruningDisposition,
    ExtremeSustainedDPSPruningService,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSGeneratedSearchBranch:
    candidate_key: str
    depth: int
    is_leaf: bool
    upper_bound: ExtremeSustainedDPSBoundEvidence
    payload: object | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.evidence, tuple):
            raise TypeError("exact sustained-DPS leaf evidence must be a tuple")
        if not isinstance(self.unresolved, tuple):
            raise TypeError("exact sustained-DPS leaf unresolved evidence must be a tuple")
        key = str(self.candidate_key or "").strip()
        if not key:
            raise ValueError("generated sustained-DPS search branch requires candidate_key")
        if isinstance(self.depth, bool) or not isinstance(self.depth, int):
            raise TypeError("generated sustained-DPS search branch depth must be an integer")
        if self.depth < 0:
            raise ValueError("generated sustained-DPS search branch depth cannot be negative")
        if not isinstance(self.is_leaf, bool):
            raise TypeError("generated sustained-DPS search branch is_leaf must be boolean")
        if not isinstance(self.upper_bound, ExtremeSustainedDPSBoundEvidence):
            raise TypeError(
                "generated sustained-DPS search branch upper_bound must be canonical bound evidence"
            )
        if str(self.upper_bound.candidate_key or "").strip() != key:
            raise ValueError(
                "generated sustained-DPS branch key must match its upper-bound evidence key"
            )
        object.__setattr__(self, "candidate_key", key)


@dataclass(frozen=True)
class ExtremeSustainedDPSExactLeafEvaluation:
    candidate_key: str
    modeled_dps: float | None
    duration_seconds: float | None
    mechanic_complete: bool
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        key = str(self.candidate_key or "").strip()
        if not key:
            raise ValueError("exact sustained-DPS leaf evaluation requires candidate_key")
        object.__setattr__(self, "candidate_key", key)
        if not isinstance(self.mechanic_complete, bool):
            raise TypeError("exact sustained-DPS leaf mechanic_complete must be boolean")

        modeled = self.modeled_dps
        if modeled is not None:
            if isinstance(modeled, bool):
                raise TypeError("exact sustained-DPS leaf modeled_dps must be numeric")
            try:
                modeled = float(modeled)
            except (TypeError, ValueError):
                raise TypeError("exact sustained-DPS leaf modeled_dps must be numeric") from None
            if not math.isfinite(modeled) or modeled < 0.0:
                raise ValueError(
                    "exact sustained-DPS leaf modeled_dps must be finite and non-negative"
                )

        duration = self.duration_seconds
        if duration is not None:
            if isinstance(duration, bool):
                raise TypeError("exact sustained-DPS leaf duration must be numeric")
            try:
                duration = float(duration)
            except (TypeError, ValueError):
                raise TypeError("exact sustained-DPS leaf duration must be numeric") from None
            if not math.isfinite(duration) or duration <= 0.0:
                raise ValueError(
                    "exact sustained-DPS leaf duration must be finite and positive"
                )

        evidence = tuple(
            dict.fromkeys(
                str(item).strip()
                for item in self.evidence
                if str(item).strip()
            )
        )
        unresolved = tuple(
            dict.fromkeys(
                str(item).strip()
                for item in self.unresolved
                if str(item).strip()
            )
        )
        object.__setattr__(self, "modeled_dps", modeled)
        object.__setattr__(self, "duration_seconds", duration)
        object.__setattr__(self, "evidence", evidence)
        object.__setattr__(self, "unresolved", unresolved)


class ExtremeSustainedDPSBranchExpander(Protocol):
    def __call__(
        self,
        branch: ExtremeSustainedDPSGeneratedSearchBranch,
    ) -> tuple[ExtremeSustainedDPSGeneratedSearchBranch, ...]: ...


class ExtremeSustainedDPSLeafEvaluator(Protocol):
    def __call__(
        self,
        branch: ExtremeSustainedDPSGeneratedSearchBranch,
    ) -> ExtremeSustainedDPSExactLeafEvaluation: ...


@dataclass(frozen=True)
class ExtremeSustainedDPSGeneratedSearchResult:
    best_modeled_dps: float | None
    best_candidates: tuple[ExtremeSustainedDPSExactLeafEvaluation, ...]
    unique_leader: ExtremeSustainedDPSExactLeafEvaluation | None
    evaluated_leaves: tuple[ExtremeSustainedDPSExactLeafEvaluation, ...]
    visited_branch_count: int
    expanded_branch_count: int
    evaluated_leaf_count: int
    pruned_branch_count: int
    forced_open_branch_count: int
    global_maximum_proven: bool
    unique_leader_proven: bool
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]

    def __post_init__(self) -> None:
        for label, value in (
            ("best_candidates", self.best_candidates),
            ("evaluated_leaves", self.evaluated_leaves),
            ("evidence", self.evidence),
            ("unresolved", self.unresolved),
        ):
            if not isinstance(value, tuple):
                raise TypeError(f"generated search result {label} must be a tuple")
        for label, value in (
            ("visited_branch_count", self.visited_branch_count),
            ("expanded_branch_count", self.expanded_branch_count),
            ("evaluated_leaf_count", self.evaluated_leaf_count),
            ("pruned_branch_count", self.pruned_branch_count),
            ("forced_open_branch_count", self.forced_open_branch_count),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(
                    f"generated search result {label} must be a non-negative integer"
                )
        if self.evaluated_leaf_count != len(self.evaluated_leaves):
            raise ValueError(
                "generated search result evaluated_leaf_count must equal evaluated_leaves length"
            )
        if any(
            not isinstance(row, ExtremeSustainedDPSExactLeafEvaluation)
            for row in self.evaluated_leaves
        ):
            raise TypeError(
                "generated search result evaluated_leaves must contain exact leaf evaluations"
            )
        if any(
            not isinstance(row, ExtremeSustainedDPSExactLeafEvaluation)
            for row in self.best_candidates
        ):
            raise TypeError(
                "generated search result best_candidates must contain exact leaf evaluations"
            )
        evaluated_keys = tuple(row.candidate_key for row in self.evaluated_leaves)
        if len(set(evaluated_keys)) != len(evaluated_keys):
            raise ValueError(
                "generated search result evaluated_leaves must have unique candidate keys"
            )
        best_keys = tuple(row.candidate_key for row in self.best_candidates)
        if len(set(best_keys)) != len(best_keys):
            raise ValueError(
                "generated search result best_candidates must have unique candidate keys"
            )
        if any(key not in set(evaluated_keys) for key in best_keys):
            raise ValueError(
                "generated search result best_candidates must come from evaluated_leaves by candidate key"
            )
        if not isinstance(self.global_maximum_proven, bool):
            raise TypeError("generated search result global_maximum_proven must be boolean")
        if not isinstance(self.unique_leader_proven, bool):
            raise TypeError("generated search result unique_leader_proven must be boolean")
        if self.unique_leader_proven and (
            not self.global_maximum_proven
            or self.unique_leader is None
            or len(self.best_candidates) != 1
        ):
            raise ValueError(
                "generated search result unique leader proof requires proven global maximum and exactly one best candidate"
            )
        if self.unique_leader is not None and (
            self.unique_leader.candidate_key not in set(best_keys)
        ):
            raise ValueError(
                "generated search result unique_leader must be one of best_candidates by candidate key"
            )

        best = self.best_modeled_dps
        if best is not None:
            if isinstance(best, bool):
                raise TypeError("generated search result best_modeled_dps must be numeric")
            try:
                best = float(best)
            except (TypeError, ValueError):
                raise TypeError(
                    "generated search result best_modeled_dps must be numeric"
                ) from None
            if not math.isfinite(best) or best < 0.0:
                raise ValueError(
                    "generated search result best_modeled_dps must be finite and non-negative"
                )
        if self.best_candidates and best is None:
            raise ValueError(
                "generated search result best_candidates require best_modeled_dps"
            )
        if best is not None and not self.best_candidates:
            raise ValueError(
                "generated search result best_modeled_dps requires retained best_candidates"
            )
        if best is not None:
            for row in self.best_candidates:
                if row.modeled_dps is None or abs(float(row.modeled_dps) - best) > 1e-9:
                    raise ValueError(
                        "generated search result best candidate DPS must match best_modeled_dps"
                    )
        if self.global_maximum_proven and (
            best is None or not self.best_candidates or self.unresolved
        ):
            raise ValueError(
                "generated search result global maximum proof requires retained best candidate evidence and no unresolved gaps"
            )

        object.__setattr__(self, "best_modeled_dps", best)
        object.__setattr__(self, "best_candidates", tuple(self.best_candidates))
        object.__setattr__(self, "evaluated_leaves", tuple(self.evaluated_leaves))
        object.__setattr__(
            self,
            "evidence",
            tuple(
                dict.fromkeys(
                    str(item).strip()
                    for item in self.evidence
                    if str(item).strip()
                )
            ),
        )
        object.__setattr__(
            self,
            "unresolved",
            tuple(
                dict.fromkeys(
                    str(item).strip()
                    for item in self.unresolved
                    if str(item).strip()
                )
            ),
        )


class ExtremeSustainedDPSGeneratedBranchAndBoundSearchService:
    """Search a finite generated denominator using only caller-proven ceilings."""

    TOLERANCE = 1e-9

    @staticmethod
    def _dedupe(values) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                str(value).strip()
                for value in values
                if str(value).strip()
            )
        )

    @classmethod
    def _priority(
        cls,
        branch: ExtremeSustainedDPSGeneratedSearchBranch,
    ) -> tuple[int, float, int, str]:
        bound = branch.upper_bound
        if bound.proven_safe and bound.upper_bound_dps is not None:
            return (
                0,
                -float(bound.upper_bound_dps),
                -int(branch.depth),
                branch.candidate_key.casefold(),
            )
        # Missing/unproven bounds must remain open. Process them before low proven
        # ceilings because exact evaluation may establish a stronger incumbent.
        return (
            -1,
            0.0,
            -int(branch.depth),
            branch.candidate_key.casefold(),
        )

    @classmethod
    def search(
        cls,
        roots: tuple[ExtremeSustainedDPSGeneratedSearchBranch, ...],
        *,
        expand_branch: ExtremeSustainedDPSBranchExpander,
        evaluate_leaf: ExtremeSustainedDPSLeafEvaluator,
        required_duration_seconds: float,
    ) -> ExtremeSustainedDPSGeneratedSearchResult:
        if isinstance(required_duration_seconds, bool):
            raise TypeError("generated sustained-DPS search duration must be numeric")
        try:
            duration = float(required_duration_seconds)
        except (TypeError, ValueError):
            raise TypeError("generated sustained-DPS search duration must be numeric") from None
        if not math.isfinite(duration) or duration <= 0.0:
            raise ValueError(
                "generated sustained-DPS search duration must be finite and positive"
            )
        if not isinstance(roots, tuple):
            raise TypeError("generated sustained-DPS search roots must be a tuple")
        if not roots:
            raise ValueError("generated sustained-DPS branch-and-bound search requires roots")
        if any(not isinstance(root, ExtremeSustainedDPSGeneratedSearchBranch) for root in roots):
            raise TypeError("generated sustained-DPS search roots must contain canonical branches")

        queue = list(roots)
        seen: set[str] = set()
        evaluated: list[ExtremeSustainedDPSExactLeafEvaluation] = []
        unresolved: list[str] = []
        evidence: list[str] = []

        incumbent = 0.0
        has_incumbent = False
        visited = 0
        expanded = 0
        pruned = 0
        forced_open = 0
        unsafe_leaf_count = 0

        while queue:
            queue.sort(key=cls._priority)
            branch = queue.pop(0)
            key = branch.candidate_key
            if key in seen:
                unresolved.append(f"Duplicate generated search branch identity: {key}")
                continue
            seen.add(key)
            visited += 1

            pruning = ExtremeSustainedDPSPruningService.prune(
                (branch.upper_bound,),
                incumbent_dps=(incumbent if has_incumbent else 0.0),
            )
            decision = pruning.decisions[0]

            if (
                has_incumbent
                and decision.disposition is ExtremeSustainedDPSPruningDisposition.PRUNED
            ):
                pruned += 1
                continue

            if decision.disposition is ExtremeSustainedDPSPruningDisposition.FORCED_OPEN:
                # A missing/unproven ceiling affects search speed, not exact-leaf
                # mechanic completeness. Once the branch is fully expanded or its
                # leaf is evaluated exactly, the absent shortcut no longer blocks
                # a global proof. Exact evaluation must carry any real mechanic gap.
                forced_open += 1

            if branch.is_leaf:
                exact = evaluate_leaf(branch)
                if not isinstance(exact, ExtremeSustainedDPSExactLeafEvaluation):
                    raise TypeError("generated sustained-DPS leaf evaluator must return canonical exact evidence")
                if exact.candidate_key != key:
                    unresolved.append(
                        f"Exact leaf evaluator returned mismatched key {exact.candidate_key!r} for {key!r}"
                    )
                    unsafe_leaf_count += 1
                    continue

                leaf_unresolved = list(exact.unresolved)
                if exact.duration_seconds is None:
                    leaf_unresolved.append("Exact leaf duration is unavailable")
                elif abs(float(exact.duration_seconds) - duration) > cls.TOLERANCE:
                    leaf_unresolved.append(
                        f"Exact leaf duration {float(exact.duration_seconds):g}s does not match "
                        f"required search horizon {duration:g}s"
                    )
                if exact.modeled_dps is None:
                    leaf_unresolved.append("Exact leaf modeled sustained DPS is unavailable")
                if not exact.mechanic_complete:
                    leaf_unresolved.append("Exact leaf mechanic evidence is incomplete")

                if leaf_unresolved:
                    unsafe_leaf_count += 1
                    unresolved.extend(
                        f"{key}: {item}"
                        for item in leaf_unresolved
                    )
                    evaluated.append(exact)
                    continue

                evaluated.append(exact)
                score = float(exact.modeled_dps)
                if not has_incumbent or score > incumbent + cls.TOLERANCE:
                    incumbent = score
                    has_incumbent = True
                continue

            children = expand_branch(branch)
            if not isinstance(children, tuple):
                raise TypeError("generated sustained-DPS branch expander must return a tuple")
            if any(not isinstance(child, ExtremeSustainedDPSGeneratedSearchBranch) for child in children):
                raise TypeError("generated sustained-DPS branch expander must return canonical branches")
            expanded += 1
            if not children:
                unresolved.append(
                    f"{key}: non-leaf generated search branch expanded to no children"
                )
                continue

            child_keys: set[str] = set()
            for child in children:
                if child.depth <= branch.depth:
                    unresolved.append(
                        f"{key}: child {child.candidate_key!r} did not advance search depth"
                    )
                if child.candidate_key in child_keys:
                    unresolved.append(
                        f"{key}: duplicate child branch identity {child.candidate_key!r}"
                    )
                    continue
                child_keys.add(child.candidate_key)
                queue.append(child)

        complete_exact = tuple(
            row
            for row in evaluated
            if row.modeled_dps is not None
            and row.duration_seconds is not None
            and abs(float(row.duration_seconds) - duration) <= cls.TOLERANCE
            and row.mechanic_complete
            and not row.unresolved
        )

        best_dps = None
        best: tuple[ExtremeSustainedDPSExactLeafEvaluation, ...] = ()
        if complete_exact:
            best_dps = max(float(row.modeled_dps) for row in complete_exact)
            best = tuple(
                row
                for row in complete_exact
                if abs(float(row.modeled_dps) - best_dps) <= cls.TOLERANCE
            )

        global_proven = (
            bool(complete_exact)
            and unsafe_leaf_count == 0
            and not unresolved
        )
        unique = (
            best[0]
            if global_proven and len(best) == 1
            else None
        )

        evidence.extend(
            (
                f"Search horizon: {duration:g}s",
                f"Visited generated branches: {visited}",
                f"Expanded non-leaf branches: {expanded}",
                f"Exact leaves evaluated: {len(evaluated)}",
                f"Safely pruned branches: {pruned}",
                f"Forced-open branches: {forced_open}",
                (
                    f"Best exact sustained DPS: {best_dps:g}"
                    if best_dps is not None
                    else "Best exact sustained DPS: unavailable"
                ),
                f"Best-candidate tie count: {len(best)}",
                "Pruning used only externally proven optimistic ceilings through ExtremeSustainedDPSPruningService",
                "Equal-to-incumbent ceilings remained open so ties could not be pruned away",
            )
        )

        return ExtremeSustainedDPSGeneratedSearchResult(
            best_modeled_dps=best_dps,
            best_candidates=best,
            unique_leader=unique,
            evaluated_leaves=tuple(evaluated),
            visited_branch_count=visited,
            expanded_branch_count=expanded,
            evaluated_leaf_count=len(evaluated),
            pruned_branch_count=pruned,
            forced_open_branch_count=forced_open,
            global_maximum_proven=global_proven,
            unique_leader_proven=bool(global_proven and len(best) == 1),
            evidence=tuple(evidence),
            unresolved=cls._dedupe(unresolved),
        )


__all__ = [
    "ExtremeSustainedDPSBranchExpander",
    "ExtremeSustainedDPSExactLeafEvaluation",
    "ExtremeSustainedDPSGeneratedBranchAndBoundSearchService",
    "ExtremeSustainedDPSGeneratedSearchBranch",
    "ExtremeSustainedDPSGeneratedSearchResult",
    "ExtremeSustainedDPSLeafEvaluator",
]
