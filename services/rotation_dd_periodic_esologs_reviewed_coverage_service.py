from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from services.rotation_dd_periodic_esologs_secondary_effect_discovery_service import (
    RotationDDPeriodicEsoLogsSecondaryEffectDiscoveryService,
)
from services.rotation_dd_periodic_runtime_semantics_review_service import (
    RotationDDPeriodicRuntimeSemanticsReviewEntry,
    RotationDDPeriodicRuntimeSemanticsReviewService,
)


@dataclass(frozen=True)
class RotationDDPeriodicEsoLogsReviewedCoverageRow:
    skill_entity_id: str
    component_count: int
    cast_count: int
    candidate_count: int
    executable_component_count: int
    unresolved_executable_fields: tuple[str, ...]
    evidence_unresolved: tuple[str, ...] = ()

    @property
    def observed(self) -> bool:
        return self.cast_count > 0


@dataclass(frozen=True)
class RotationDDPeriodicEsoLogsReviewedCoverageReport:
    rows: tuple[RotationDDPeriodicEsoLogsReviewedCoverageRow, ...]

    @property
    def observed_rows(self) -> tuple[RotationDDPeriodicEsoLogsReviewedCoverageRow, ...]:
        return tuple(row for row in self.rows if row.observed)


class RotationDDPeriodicEsoLogsReviewedCoverageService:
    """Report which reviewed DD periodic skills are represented in an ESO Logs corpus.

    This is a composition layer only. Reviewed identities come from the periodic review
    registry and cast/candidate observations come from the existing secondary-effect
    discovery service. It does not parse combat events independently and never promotes
    observational evidence into executable runtime semantics.
    """

    def __init__(
        self,
        *,
        canonical_database_path: str | Path,
        logs_database_path: str | Path,
        review_service: RotationDDPeriodicRuntimeSemanticsReviewService | None = None,
        discovery_service: RotationDDPeriodicEsoLogsSecondaryEffectDiscoveryService | None = None,
    ) -> None:
        self.review_service = review_service or RotationDDPeriodicRuntimeSemanticsReviewService()
        self.discovery_service = discovery_service or RotationDDPeriodicEsoLogsSecondaryEffectDiscoveryService(
            canonical_database_path=canonical_database_path,
            logs_database_path=logs_database_path,
            review_service=self.review_service,
        )

    def inspect(self) -> RotationDDPeriodicEsoLogsReviewedCoverageReport:
        grouped: dict[str, list[RotationDDPeriodicRuntimeSemanticsReviewEntry]] = {}
        for entry in self.review_service.load():
            grouped.setdefault(entry.skill_entity_id, []).append(entry)

        rows: list[RotationDDPeriodicEsoLogsReviewedCoverageRow] = []
        for skill_entity_id, entries in grouped.items():
            discovery = self.discovery_service.inspect_skill(skill_entity_id)
            unresolved_fields = tuple(
                sorted(
                    {
                        field_name
                        for entry in entries
                        for field_name in entry.unresolved_executable_fields
                    }
                )
            )
            rows.append(
                RotationDDPeriodicEsoLogsReviewedCoverageRow(
                    skill_entity_id=skill_entity_id,
                    component_count=len(entries),
                    cast_count=discovery.cast_count,
                    candidate_count=len(discovery.candidates),
                    executable_component_count=sum(1 for entry in entries if entry.executable_complete),
                    unresolved_executable_fields=unresolved_fields,
                    evidence_unresolved=tuple(discovery.unresolved),
                )
            )

        rows.sort(
            key=lambda row: (
                -int(row.observed),
                -row.cast_count,
                row.skill_entity_id,
            )
        )
        return RotationDDPeriodicEsoLogsReviewedCoverageReport(rows=tuple(rows))


__all__ = [
    "RotationDDPeriodicEsoLogsReviewedCoverageReport",
    "RotationDDPeriodicEsoLogsReviewedCoverageRow",
    "RotationDDPeriodicEsoLogsReviewedCoverageService",
]
