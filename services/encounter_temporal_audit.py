from __future__ import annotations

"""Read-only coverage audit for source-qualified encounter timing evidence."""

from dataclasses import dataclass

from services.encounter_service import EncounterService


@dataclass(frozen=True)
class EncounterTemporalAuditRow:
    encounter_id: str
    fact_id: str
    fact_type: str
    fact_key: str
    value_key: str
    seconds: float
    approximate: bool
    reconciliation_status: str
    distinct_sources: int


@dataclass(frozen=True)
class EncounterTemporalAudit:
    rows: tuple[EncounterTemporalAuditRow, ...]

    @property
    def temporal_value_count(self) -> int:
        return len(self.rows)

    @property
    def exact_value_count(self) -> int:
        return sum(not row.approximate for row in self.rows)

    @property
    def approximate_value_count(self) -> int:
        return sum(row.approximate for row in self.rows)

    @property
    def corroborated_value_count(self) -> int:
        return sum(row.reconciliation_status == "corroborated" for row in self.rows)

    @property
    def single_source_value_count(self) -> int:
        return sum(row.reconciliation_status == "single_source" for row in self.rows)

    @property
    def encounter_count(self) -> int:
        return len({row.encounter_id for row in self.rows})


def audit_encounter_temporal_evidence(service: EncounterService) -> EncounterTemporalAudit:
    """Report timing evidence coverage without promoting it to encounter canon."""
    rows = []
    for encounter_id in service.encounter_ids():
        for temporal in service.temporal_evidence(encounter_id):
            rows.append(
                EncounterTemporalAuditRow(
                    encounter_id=encounter_id,
                    fact_id=temporal.fact_id,
                    fact_type=temporal.fact_type,
                    fact_key=temporal.fact_key,
                    value_key=temporal.value_key,
                    seconds=temporal.seconds,
                    approximate=temporal.approximate,
                    reconciliation_status=temporal.reconciliation_status,
                    distinct_sources=temporal.distinct_sources,
                )
            )
    return EncounterTemporalAudit(tuple(rows))
