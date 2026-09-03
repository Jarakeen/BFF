from __future__ import annotations

"""Load source-separated encounter evidence packets from JSON."""

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from services.encounter_evidence import EncounterEvidence


@dataclass(frozen=True)
class EncounterEvidencePacket:
    path: Path
    schema_version: int
    content_id: str
    encounter_id: str
    encounter_name: str
    evidence: tuple[EncounterEvidence, ...]


def _clean(value: Any) -> str:
    return str(value or "").strip()


def load_encounter_evidence_packet(path: Path) -> EncounterEvidencePacket:
    path = Path(path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Unable to read encounter evidence packet {path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise ValueError(f"Encounter evidence packet must contain a JSON object: {path}")

    encounter_id = _clean(payload.get("encounter_id"))
    if not encounter_id:
        raise ValueError(f"Encounter evidence packet is missing encounter_id: {path}")

    raw_evidence = payload.get("evidence", [])
    if not isinstance(raw_evidence, list):
        raise ValueError(f"Encounter evidence packet evidence must be a list: {path}")

    rows: list[EncounterEvidence] = []
    for index, raw in enumerate(raw_evidence, start=1):
        if not isinstance(raw, dict):
            raise ValueError(
                f"Encounter evidence row {index} must be an object: {path}"
            )
        try:
            rows.append(
                EncounterEvidence(
                    encounter_id=_clean(raw.get("encounter_id")) or encounter_id,
                    fact_type=str(raw["fact_type"]),
                    fact_key=str(raw["fact_key"]),
                    value=raw.get("value"),
                    source_type=str(raw["source_type"]),
                    source_name=str(raw["source_name"]),
                    source_locator=_clean(raw.get("source_locator")),
                    source_revision=_clean(raw.get("source_revision")),
                    source_family=_clean(raw.get("source_family")),
                    game_update=_clean(raw.get("game_update")),
                    patch_version=_clean(raw.get("patch_version")),
                    confidence=_clean(raw.get("confidence")) or "medium",
                    notes=_clean(raw.get("notes")),
                )
            )
        except (KeyError, ValueError) as exc:
            raise ValueError(
                f"Invalid encounter evidence row {index} in {path}: {exc}"
            ) from exc

    schema_version_raw = payload.get("schema_version", 1)
    try:
        schema_version = int(schema_version_raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Encounter evidence packet has invalid schema_version {schema_version_raw!r}: {path}"
        ) from exc

    return EncounterEvidencePacket(
        path=path,
        schema_version=schema_version,
        content_id=_clean(payload.get("content_id")),
        encounter_id=encounter_id,
        encounter_name=_clean(payload.get("encounter_name")) or encounter_id,
        evidence=tuple(rows),
    )
