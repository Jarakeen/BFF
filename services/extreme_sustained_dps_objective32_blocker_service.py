from __future__ import annotations

"""Structured blockers for theoretical MOST Sustained DPS closure."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ExtremeSustainedDPSObjective32Blocker:
    code: str
    category: str
    detail: str
    axis: str | None = None
    source: str = ""

    def __post_init__(self) -> None:
        for field_name in ("code", "category", "detail"):
            value = str(getattr(self, field_name) or "").strip()
            if not value:
                raise ValueError(f"Objective #32 blocker {field_name} is required")
            object.__setattr__(self, field_name, value)
        if self.axis is not None:
            object.__setattr__(
                self,
                "axis",
                str(self.axis).strip() or None,
            )
        object.__setattr__(self, "source", str(self.source or "").strip())


@dataclass(frozen=True)
class ExtremeSustainedDPSObjective32BlockerReport:
    blockers: tuple[ExtremeSustainedDPSObjective32Blocker, ...]
    evidence: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.blockers, tuple):
            raise TypeError("Objective #32 blocker report blockers must be a tuple")
        if not isinstance(self.evidence, tuple):
            raise TypeError("Objective #32 blocker report evidence must be a tuple")
        if any(
            not isinstance(row, ExtremeSustainedDPSObjective32Blocker)
            for row in self.blockers
        ):
            raise TypeError("Objective #32 blocker report requires canonical blocker records")
        object.__setattr__(self, "blockers", tuple(self.blockers))
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

    @property
    def closed(self) -> bool:
        return not self.blockers


class ExtremeSustainedDPSObjective32BlockerService:
    """Explain theoretical closure debt without changing proof semantics."""

    @staticmethod
    def _proof_tuple(owner: object, field: str, label: str) -> tuple:
        value = getattr(owner, field, ())
        if not isinstance(value, tuple):
            raise TypeError(f"Objective #32 {label} {field} must be a tuple")
        return value

    @classmethod
    def assess(
        cls,
        *,
        search_result: object,
        axis_inventory: object,
        axis_coverage: object,
        closure: object,
        closure_inventory: object | None = None,
    ) -> ExtremeSustainedDPSObjective32BlockerReport:
        blockers: list[ExtremeSustainedDPSObjective32Blocker] = []

        global_maximum_proven = getattr(search_result, "global_maximum_proven", None)
        if not isinstance(global_maximum_proven, bool):
            raise TypeError(
                "Objective #32 blocker assessment requires boolean global_maximum_proven"
            )
        if not global_maximum_proven:
            blockers.append(
                ExtremeSustainedDPSObjective32Blocker(
                    code="finite_denominator_open",
                    category="search",
                    detail=(
                        "Generated branch-and-bound has not proven the maximum over "
                        "its current finite denominator."
                    ),
                    source="generated search",
                )
            )

        for item in cls._proof_tuple(search_result, "unresolved", "search result"):
            detail = str(item).strip()
            if detail:
                blockers.append(
                    ExtremeSustainedDPSObjective32Blocker(
                        code="search_evidence_unresolved",
                        category="search",
                        detail=detail,
                        source="generated search",
                    )
                )

        for axis in cls._proof_tuple(axis_inventory, "missing_canonical_axes", "axis inventory"):
            blockers.append(
                ExtremeSustainedDPSObjective32Blocker(
                    code="physical_axis_missing",
                    category="tree",
                    axis=str(axis),
                    detail=(
                        f"Canonical mutation axis {axis!r} is not physically "
                        "enumerated by the generated search tree."
                    ),
                    source="generated axis inventory",
                )
            )

        for axis in cls._proof_tuple(axis_inventory, "duplicate_canonical_axes", "axis inventory"):
            blockers.append(
                ExtremeSustainedDPSObjective32Blocker(
                    code="physical_axis_duplicate",
                    category="tree",
                    axis=str(axis),
                    detail=(
                        f"Canonical mutation axis {axis!r} is enumerated more than "
                        "once by the generated search tree."
                    ),
                    source="generated axis inventory",
                )
            )

        for item in cls._proof_tuple(axis_inventory, "unresolved", "axis inventory"):
            detail = str(item).strip()
            if detail:
                blockers.append(
                    ExtremeSustainedDPSObjective32Blocker(
                        code="tree_inventory_unresolved",
                        category="tree",
                        detail=detail,
                        source="generated axis inventory",
                    )
                )

        for axis in cls._proof_tuple(axis_coverage, "missing_axes", "axis coverage"):
            blockers.append(
                ExtremeSustainedDPSObjective32Blocker(
                    code="axis_coverage_missing",
                    category="coverage",
                    axis=str(axis),
                    detail=(
                        f"Canonical mutation axis {axis!r} does not have complete "
                        "coverage proof."
                    ),
                    source="axis coverage composition",
                )
            )

        for item in cls._proof_tuple(axis_coverage, "unresolved", "axis coverage"):
            detail = str(item).strip()
            if detail:
                blockers.append(
                    ExtremeSustainedDPSObjective32Blocker(
                        code="axis_coverage_unresolved",
                        category="coverage",
                        detail=detail,
                        source="axis coverage composition",
                    )
                )

        for item in cls._proof_tuple(closure, "omitted_scope", "theoretical closure"):
            detail = str(item).strip()
            if detail:
                blockers.append(
                    ExtremeSustainedDPSObjective32Blocker(
                        code="theoretical_scope_omitted",
                        category="theory",
                        detail=detail,
                        source="theoretical closure gate",
                    )
                )

        for item in cls._proof_tuple(closure, "unresolved", "theoretical closure"):
            detail = str(item).strip()
            if detail and "scope remains explicitly omitted" not in detail:
                blockers.append(
                    ExtremeSustainedDPSObjective32Blocker(
                        code="theoretical_closure_unresolved",
                        category="theory",
                        detail=detail,
                        source="theoretical closure gate",
                    )
                )

        if closure_inventory is not None:
            for item in cls._proof_tuple(
                closure_inventory, "source_data_blockers", "closure inventory"
            ):
                detail = str(item).strip()
                if detail:
                    blockers.append(
                        ExtremeSustainedDPSObjective32Blocker(
                            code="runtime_source_data_unresolved",
                            category="source_data",
                            detail=detail,
                            source="runtime closure inventory",
                        )
                    )

            for item in cls._proof_tuple(
                closure_inventory, "math_review_blockers", "closure inventory"
            ):
                detail = str(item).strip()
                if detail:
                    blockers.append(
                        ExtremeSustainedDPSObjective32Blocker(
                            code="runtime_math_review_unresolved",
                            category="math_review",
                            detail=detail,
                            source="runtime closure inventory",
                        )
                    )

            for gap in cls._proof_tuple(
                closure_inventory, "mechanics_blockers", "closure inventory"
            ):
                blockers.append(
                    ExtremeSustainedDPSObjective32Blocker(
                        code="mechanics_coverage_missing_critical",
                        category="mechanics",
                        detail=str(getattr(gap, "needed_evidence", gap)).strip(),
                        source=str(getattr(gap, "key", "canonical mechanics coverage")),
                    )
                )

            for gap in cls._proof_tuple(
                closure_inventory, "mechanics_advisories", "closure inventory"
            ):
                blockers.append(
                    ExtremeSustainedDPSObjective32Blocker(
                        code="mechanics_coverage_partial",
                        category="mechanics",
                        detail=str(getattr(gap, "needed_evidence", gap)).strip(),
                        source=str(getattr(gap, "key", "canonical mechanics coverage")),
                    )
                )

        unique: list[ExtremeSustainedDPSObjective32Blocker] = []
        seen: set[tuple[str, str | None, str]] = set()
        for blocker in blockers:
            key = (blocker.code, blocker.axis, blocker.detail)
            if key in seen:
                continue
            seen.add(key)
            unique.append(blocker)

        return ExtremeSustainedDPSObjective32BlockerReport(
            blockers=tuple(unique),
            evidence=(
                f"Objective #32 blockers: {len(unique)}",
                f"Search blockers: {sum(row.category == 'search' for row in unique)}",
                f"Tree blockers: {sum(row.category == 'tree' for row in unique)}",
                f"Coverage blockers: {sum(row.category == 'coverage' for row in unique)}",
                f"Theoretical-scope blockers: {sum(row.category == 'theory' for row in unique)}",
                f"Runtime source-data blockers: {sum(row.category == 'source_data' for row in unique)}",
                f"Runtime math/review blockers: {sum(row.category == 'math_review' for row in unique)}",
                f"Mechanics-coverage blockers: {sum(row.category == 'mechanics' for row in unique)}",
                "Blocker reporting is diagnostic only and cannot create or remove proof.",
            ),
        )


__all__ = [
    "ExtremeSustainedDPSObjective32Blocker",
    "ExtremeSustainedDPSObjective32BlockerReport",
    "ExtremeSustainedDPSObjective32BlockerService",
]
