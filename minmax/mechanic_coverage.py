from __future__ import annotations

from dataclasses import dataclass


CoverageStatus = str
VALID_COVERAGE_STATUSES = frozenset(
    {"implemented", "conditional", "unresolved", "irrelevant"}
)
SUPPORTED_COVERAGE_STATUSES = frozenset({"implemented", "conditional"})


@dataclass(frozen=True)
class MechanicCoverageItem:
    """One auditable mechanic in a shared BFF coverage denominator.

    ``conditional`` means the mechanic is supported when its explicit scenario
    evidence is supplied. It is covered behavior, not an unresolved gap.
    ``unresolved`` is the fail-closed state that blocks a completeness claim.
    ``irrelevant`` stays visible for auditability but does not enter the
    objective's denominator.
    """

    mechanic_id: str
    category: str
    status: CoverageStatus
    evidence: str
    detail: str

    @property
    def counts_toward_denominator(self) -> bool:
        return self.status != "irrelevant"

    @property
    def is_supported(self) -> bool:
        return self.status in SUPPORTED_COVERAGE_STATUSES

    @property
    def is_fully_covered(self) -> bool:
        """Compatibility spelling for callers that ask whether coverage exists."""

        return self.is_supported

    @property
    def is_blocker(self) -> bool:
        return self.status == "unresolved"


@dataclass(frozen=True)
class MechanicCoverageSummary:
    implemented: int
    conditional: int
    unresolved: int
    irrelevant: int
    denominator: int
    covered: int
    blocker_ids: tuple[str, ...]

    @property
    def coverage_fraction(self) -> float:
        if self.denominator == 0:
            return 1.0
        return self.covered / self.denominator

    @property
    def complete(self) -> bool:
        return self.covered == self.denominator and not self.blocker_ids


def validate_mechanic_coverage(
    rows: tuple[MechanicCoverageItem, ...],
    *,
    required_categories: tuple[str, ...] = (),
) -> None:
    ids = tuple(row.mechanic_id for row in rows)
    if len(ids) != len(set(ids)):
        raise ValueError("mechanic coverage contains duplicate mechanic ids")

    invalid = tuple(row.status for row in rows if row.status not in VALID_COVERAGE_STATUSES)
    if invalid:
        raise ValueError(f"mechanic coverage has invalid status: {invalid[0]}")

    categories = {row.category for row in rows}
    missing = tuple(category for category in required_categories if category not in categories)
    if missing:
        raise ValueError(
            "mechanic coverage is missing required categories: " + ", ".join(missing)
        )


def summarize_mechanic_coverage(
    rows: tuple[MechanicCoverageItem, ...],
    *,
    required_categories: tuple[str, ...] = (),
) -> MechanicCoverageSummary:
    """Summarize coverage with conditional-but-proven mechanics counted as covered.

    This contract is intentionally role-neutral. Extreme, Comp Maker, Team
    Optimization, Rotation, provider/coverage, and other BFF consumers can use
    the same denominator semantics without inventing feature-local meanings for
    "conditional" or "unresolved".
    """

    validate_mechanic_coverage(rows, required_categories=required_categories)
    counts = {
        status: sum(1 for row in rows if row.status == status)
        for status in VALID_COVERAGE_STATUSES
    }
    denominator = sum(row.counts_toward_denominator for row in rows)
    covered = sum(
        row.counts_toward_denominator and row.is_supported
        for row in rows
    )
    blockers = tuple(row.mechanic_id for row in rows if row.is_blocker)
    return MechanicCoverageSummary(
        implemented=counts["implemented"],
        conditional=counts["conditional"],
        unresolved=counts["unresolved"],
        irrelevant=counts["irrelevant"],
        denominator=denominator,
        covered=covered,
        blocker_ids=blockers,
    )
