from __future__ import annotations

"""Source-separated evidence reconciliation for encounter facts.

This module deliberately sits in front of the canonical encounter layer.
Evidence from UESP, combat addons, guides, logs, or manual research remains
independently attributable until a later promotion step decides that a fact is
safe to write canonically.
"""

from dataclasses import dataclass
import json
from typing import Any, Iterable


VALID_CONFIDENCE = {"low", "medium", "high"}
VALID_RECONCILIATION_STATUS = {"single_source", "corroborated", "conflicting"}


@dataclass(frozen=True)
class EncounterEvidence:
    encounter_id: str
    fact_type: str
    fact_key: str
    value: Any
    source_type: str
    source_name: str
    source_locator: str = ""
    source_revision: str = ""
    game_update: str = ""
    patch_version: str = ""
    confidence: str = "medium"
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.encounter_id.strip():
            raise ValueError("encounter_id is required")
        if not self.fact_type.strip():
            raise ValueError("fact_type is required")
        if not self.fact_key.strip():
            raise ValueError("fact_key is required")
        if not self.source_type.strip():
            raise ValueError("source_type is required")
        if not self.source_name.strip():
            raise ValueError("source_name is required")
        if self.confidence not in VALID_CONFIDENCE:
            raise ValueError(
                f"confidence must be one of {sorted(VALID_CONFIDENCE)}; "
                f"got {self.confidence!r}"
            )

    @property
    def source_identity(self) -> tuple[str, str, str, str]:
        return (
            self.source_type.strip().casefold(),
            self.source_name.strip().casefold(),
            self.source_locator.strip(),
            self.source_revision.strip(),
        )

    @property
    def fact_identity(self) -> tuple[str, str, str]:
        return (
            self.encounter_id.strip(),
            self.fact_type.strip().casefold(),
            self.fact_key.strip().casefold(),
        )


@dataclass(frozen=True)
class ReconciledEncounterFact:
    encounter_id: str
    fact_type: str
    fact_key: str
    status: str
    value: Any | None
    evidence: tuple[EncounterEvidence, ...]
    distinct_sources: int
    distinct_values: int

    @property
    def safe_for_review(self) -> bool:
        """True when evidence agrees; promotion still requires an explicit step."""
        return self.status in {"single_source", "corroborated"}


def _normalized_value(value: Any) -> str:
    """Stable comparison representation without changing the stored value."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def reconcile_encounter_evidence(
    evidence_rows: Iterable[EncounterEvidence],
) -> list[ReconciledEncounterFact]:
    """Group source evidence into reviewable encounter facts.

    Rules are deliberately conservative:
      * one distinct source + one value -> single_source
      * two or more distinct sources agreeing -> corroborated
      * any disagreement in values -> conflicting

    This function never chooses a winner when sources disagree and never writes
    to the canonical encounter database.
    """

    grouped: dict[tuple[str, str, str], list[EncounterEvidence]] = {}
    for row in evidence_rows:
        grouped.setdefault(row.fact_identity, []).append(row)

    results: list[ReconciledEncounterFact] = []

    for identity in sorted(grouped):
        rows = grouped[identity]
        values: dict[str, Any] = {}
        sources = set()

        for row in rows:
            values.setdefault(_normalized_value(row.value), row.value)
            sources.add(row.source_identity)

        if len(values) > 1:
            status = "conflicting"
            resolved_value = None
        elif len(sources) > 1:
            status = "corroborated"
            resolved_value = next(iter(values.values()))
        else:
            status = "single_source"
            resolved_value = next(iter(values.values()))

        results.append(
            ReconciledEncounterFact(
                encounter_id=rows[0].encounter_id,
                fact_type=rows[0].fact_type,
                fact_key=rows[0].fact_key,
                status=status,
                value=resolved_value,
                evidence=tuple(rows),
                distinct_sources=len(sources),
                distinct_values=len(values),
            )
        )

    return results
