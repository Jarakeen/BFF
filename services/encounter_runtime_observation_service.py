from __future__ import annotations

"""Load reviewed encounter runtime observations without promoting them to mechanics.

Runtime observations are empirical strategy evidence derived from repeated combat
telemetry. They may inform guide prose and coaching, but they are intentionally
separate from encounter_canonical_fact, encounter_mechanic, and raw source imports.
"""

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


_ALLOWED_OBSERVATION_TYPES = {"runtime_strategy_evidence"}
_ALLOWED_STATUSES = {"reviewed"}
_ALLOWED_CONFIDENCE = {"repeated_observation"}


@dataclass(frozen=True, slots=True)
class EncounterRuntimeObservationConclusion:
    key: str
    statement: str
    confidence: str


@dataclass(frozen=True, slots=True)
class EncounterRuntimeStrategyImplication:
    role: str
    priority: str
    guidance: str


@dataclass(frozen=True, slots=True)
class EncounterRuntimeObservation:
    schema_version: int
    encounter_id: str
    content_id: str
    observation_key: str
    observation_type: str
    status: str
    source_type: str
    source_name: str
    source_reports: tuple[str, ...]
    sample: dict[str, Any]
    semantic_mechanic_key: str
    findings: dict[str, Any]
    reviewed_conclusions: tuple[EncounterRuntimeObservationConclusion, ...]
    strategy_implications: tuple[EncounterRuntimeStrategyImplication, ...]
    limitations: tuple[str, ...]

    @property
    def successful_kills(self) -> int:
        return int(self.sample.get("successful_kills", 0) or 0)

    @property
    def reviewed_window_count(self) -> int:
        return int(self.sample.get("reviewed_flight_windows", 0) or 0)


class EncounterRuntimeObservationService:
    """Read and validate reviewed runtime-strategy observation records."""

    def load(self, path: Path) -> EncounterRuntimeObservation:
        path = Path(path)
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Encounter runtime observation must be a JSON object.")
        return self.from_payload(payload)

    def from_payload(self, payload: dict[str, Any]) -> EncounterRuntimeObservation:
        schema_version = self._positive_int(payload.get("schema_version"), "schema_version")
        if schema_version != 1:
            raise ValueError(f"Unsupported encounter runtime observation schema_version={schema_version}.")

        observation_type = self._required_text(payload, "observation_type")
        if observation_type not in _ALLOWED_OBSERVATION_TYPES:
            raise ValueError(
                "Encounter runtime observations must remain runtime strategy evidence; "
                f"got observation_type={observation_type!r}."
            )

        status = self._required_text(payload, "status")
        if status not in _ALLOWED_STATUSES:
            raise ValueError(f"Encounter runtime observation status must be reviewed; got {status!r}.")

        sample = payload.get("sample")
        if not isinstance(sample, dict):
            raise ValueError("Encounter runtime observation requires a sample object.")
        successful_kills = self._positive_int(sample.get("successful_kills"), "sample.successful_kills")
        reviewed_windows = self._positive_int(
            sample.get("reviewed_flight_windows"),
            "sample.reviewed_flight_windows",
        )
        if reviewed_windows < successful_kills:
            raise ValueError("reviewed_flight_windows cannot be smaller than successful_kills.")

        findings = payload.get("findings")
        if not isinstance(findings, dict) or not findings:
            raise ValueError("Encounter runtime observation requires non-empty findings.")

        conclusions_raw = payload.get("reviewed_conclusions")
        if not isinstance(conclusions_raw, list) or not conclusions_raw:
            raise ValueError("Encounter runtime observation requires reviewed_conclusions.")
        conclusions: list[EncounterRuntimeObservationConclusion] = []
        seen_conclusion_keys: set[str] = set()
        for row in conclusions_raw:
            if not isinstance(row, dict):
                raise ValueError("Each reviewed conclusion must be an object.")
            key = self._required_text(row, "key")
            if key in seen_conclusion_keys:
                raise ValueError(f"Duplicate reviewed conclusion key: {key}")
            seen_conclusion_keys.add(key)
            confidence = self._required_text(row, "confidence")
            if confidence not in _ALLOWED_CONFIDENCE:
                raise ValueError(f"Unsupported runtime observation confidence: {confidence!r}.")
            conclusions.append(
                EncounterRuntimeObservationConclusion(
                    key=key,
                    statement=self._required_text(row, "statement"),
                    confidence=confidence,
                )
            )

        implications_raw = payload.get("strategy_implications")
        if not isinstance(implications_raw, list) or not implications_raw:
            raise ValueError("Encounter runtime observation requires strategy_implications.")
        implications: list[EncounterRuntimeStrategyImplication] = []
        for row in implications_raw:
            if not isinstance(row, dict):
                raise ValueError("Each strategy implication must be an object.")
            implications.append(
                EncounterRuntimeStrategyImplication(
                    role=self._required_text(row, "role"),
                    priority=self._required_text(row, "priority"),
                    guidance=self._required_text(row, "guidance"),
                )
            )

        reports_raw = payload.get("source_reports")
        if not isinstance(reports_raw, list) or not reports_raw:
            raise ValueError("Encounter runtime observation requires source_reports.")
        reports = tuple(str(value).strip() for value in reports_raw if str(value).strip())
        if not reports:
            raise ValueError("Encounter runtime observation source_reports cannot be empty.")

        limitations_raw = payload.get("limitations")
        if not isinstance(limitations_raw, list) or not limitations_raw:
            raise ValueError("Encounter runtime observation requires limitations.")
        limitations = tuple(str(value).strip() for value in limitations_raw if str(value).strip())
        if not limitations:
            raise ValueError("Encounter runtime observation limitations cannot be empty.")

        return EncounterRuntimeObservation(
            schema_version=schema_version,
            encounter_id=self._required_text(payload, "encounter_id"),
            content_id=self._required_text(payload, "content_id"),
            observation_key=self._required_text(payload, "observation_key"),
            observation_type=observation_type,
            status=status,
            source_type=self._required_text(payload, "source_type"),
            source_name=self._required_text(payload, "source_name"),
            source_reports=reports,
            sample=dict(sample),
            semantic_mechanic_key=self._required_text(payload, "semantic_mechanic_key"),
            findings=dict(findings),
            reviewed_conclusions=tuple(conclusions),
            strategy_implications=tuple(implications),
            limitations=limitations,
        )

    @staticmethod
    def _required_text(payload: dict[str, Any], key: str) -> str:
        value = str(payload.get(key) or "").strip()
        if not value:
            raise ValueError(f"Encounter runtime observation requires {key}.")
        return value

    @staticmethod
    def _positive_int(value: Any, key: str) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Encounter runtime observation requires integer {key}.") from exc
        if parsed <= 0:
            raise ValueError(f"Encounter runtime observation requires positive {key}.")
        return parsed


__all__ = [
    "EncounterRuntimeObservation",
    "EncounterRuntimeObservationConclusion",
    "EncounterRuntimeObservationService",
    "EncounterRuntimeStrategyImplication",
]
