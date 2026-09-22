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

    @property
    def closed(self) -> bool:
        return not self.blockers


class ExtremeSustainedDPSObjective32BlockerService:
    """Explain theoretical closure debt without changing proof semantics."""

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

        if not bool(getattr(search_result, "global_maximum_proven", False)):
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

        for item in tuple(getattr(search_result, "unresolved", ()) or ()):
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

        for axis in tuple(
            getattr(axis_inventory, "missing_canonical_axes", ()) or ()
        ):
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

        for axis in tuple(
            getattr(axis_inventory, "duplicate_canonical_axes", ()) or ()
        ):
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

        for item in tuple(getattr(axis_inventory, "unresolved", ()) or ()):
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

        for axis in tuple(getattr(axis_coverage, "missing_axes", ()) or ()):
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

        for item in tuple(getattr(axis_coverage, "unresolved", ()) or ()):
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

        for item in tuple(getattr(closure, "omitted_scope", ()) or ()):
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

        if closure_inventory is not None:
            for item in tuple(
                getattr(closure_inventory, "source_data_blockers", ()) or ()
            ):
                detail = str(item).strip()
                if detail:
                    blockers.append(
                        ExtremeSustainedDPSObjective32Blocker(
                            code="runtime_source_data_unresolved",
                            category="source_data",
                            detail=detail,
                            source="runtime relevance closure inventory",
                        )
                    )

            for item in tuple(
                getattr(closure_inventory, "math_review_blockers", ()) or ()
            ):
                detail = str(item).strip()
                if detail:
                    blockers.append(
                        ExtremeSustainedDPSObjective32Blocker(
                            code="runtime_math_review_unresolved",
                            category="math_review",
                            detail=detail,
                            source="runtime relevance closure inventory",
                        )
                    )

            for gap in tuple(
                getattr(closure_inventory, "mechanics_blockers", ()) or ()
            ):
                blockers.append(
                    ExtremeSustainedDPSObjective32Blocker(
                        code="mechanics_coverage_missing_critical",
                        category="mechanics",
                        detail=str(getattr(gap, "needed_evidence", gap)).strip(),
                        source=str(getattr(gap, "key", "canonical mechanics coverage")),
                    )
                )

            for gap in tuple(
                getattr(closure_inventory, "mechanics_advisories", ()) or ()
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
