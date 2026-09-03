from __future__ import annotations

"""Project tracked ESO boss source JSON into encounter review evidence.

The source corpus is evidence, not canonical truth. This module deliberately
stops before canonical persistence: every projected row is an EncounterEvidence
record and therefore remains subject to the existing reconciliation, review,
and promotion policy.
"""

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any, Iterable

from services.encounter_evidence import EncounterEvidence


@dataclass(frozen=True)
class BossEncounterProjection:
    source_path: Path
    content_id: str
    encounter_id: str
    encounter_name: str
    evidence: tuple[EncounterEvidence, ...]
    mechanic_count: int
    ability_count: int
    phase_count: int
    inferred_mechanic_count: int
    incomplete_mechanic_count: int


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")


def _clean_dict(value: dict[str, Any], *, excluded: Iterable[str] = ()) -> dict[str, Any]:
    excluded_set = set(excluded)
    return {key: item for key, item in value.items() if key not in excluded_set}


def _source_fields(payload: dict[str, Any]) -> dict[str, str]:
    source = payload.get("source") if isinstance(payload.get("source"), dict) else {}
    page_title = str(source.get("page_title") or payload.get("name") or "ESO boss source").strip()
    revision = str(source.get("revision_id") or "").strip()
    retrieved_at = str(source.get("retrieved_at") or "").strip()
    notes = f"retrieved_at={retrieved_at}" if retrieved_at else ""
    return {
        "source_type": "uesp",
        "source_name": f"UESP {page_title}",
        "source_locator": str(source.get("url") or "").strip(),
        "source_revision": revision,
        "source_family": "uesp",
        "notes": notes,
    }


def _evidence(
    *,
    encounter_id: str,
    fact_type: str,
    fact_key: str,
    value: Any,
    source: dict[str, str],
    locator_suffix: str,
    confidence: str,
    notes: str = "",
) -> EncounterEvidence:
    locator = source["source_locator"]
    if locator_suffix:
        locator = f"{locator}#{locator_suffix}" if locator else locator_suffix
    source_notes = source["notes"]
    combined_notes = "\n".join(part for part in (source_notes, notes.strip()) if part)
    return EncounterEvidence(
        encounter_id=encounter_id,
        fact_type=fact_type,
        fact_key=fact_key,
        value=value,
        source_type=source["source_type"],
        source_name=source["source_name"],
        source_locator=locator,
        source_revision=source["source_revision"],
        source_family=source["source_family"],
        confidence=confidence,
        notes=combined_notes,
    )


def project_boss_payload(
    payload: dict[str, Any],
    *,
    source_path: Path = Path("<memory>"),
) -> BossEncounterProjection:
    encounter_id = str(payload.get("id") or "").strip()
    encounter_name = str(payload.get("name") or "").strip()
    content_id = str(payload.get("content_id") or "").strip()
    if not encounter_id:
        raise ValueError(f"Boss source has no id: {source_path}")
    if not encounter_name:
        raise ValueError(f"Boss source has no name: {source_path}")

    source = _source_fields(payload)
    rows: list[EncounterEvidence] = []
    inferred = 0
    incomplete = 0

    mechanics = payload.get("mechanics") if isinstance(payload.get("mechanics"), list) else []
    for index, raw in enumerate(mechanics):
        if not isinstance(raw, dict):
            incomplete += 1
            continue
        name = str(raw.get("name") or "").strip()
        if not name:
            incomplete += 1
            continue
        key = _slug(name) or f"mechanic_{index + 1}"
        interpretation = str(raw.get("interpretation_status") or "").strip().casefold()
        confidence = "medium" if interpretation == "inferred" else "high"
        if interpretation == "inferred":
            inferred += 1

        rows.append(
            _evidence(
                encounter_id=encounter_id,
                fact_type="mechanic_state",
                fact_key=f"{key}_exists",
                value=True,
                source=source,
                locator_suffix=f"mechanic-{key}",
                confidence=confidence,
                notes=f"interpretation_status={interpretation}" if interpretation else "",
            )
        )
        detail = _clean_dict(raw, excluded=("links",))
        rows.append(
            _evidence(
                encounter_id=encounter_id,
                fact_type="mechanic_detail",
                fact_key=f"{key}_detail",
                value=detail,
                source=source,
                locator_suffix=f"mechanic-{key}",
                confidence=confidence,
                notes=f"interpretation_status={interpretation}" if interpretation else "",
            )
        )
        if not raw.get("mechanic_type"):
            incomplete += 1

    abilities = payload.get("abilities") if isinstance(payload.get("abilities"), list) else []
    mechanic_names = {
        str(raw.get("name") or "").strip().casefold()
        for raw in mechanics
        if isinstance(raw, dict) and str(raw.get("name") or "").strip()
    }
    for index, raw in enumerate(abilities):
        if not isinstance(raw, dict):
            continue
        name = str(raw.get("name") or "").strip()
        if not name or name.casefold() in mechanic_names:
            continue
        key = _slug(name) or f"ability_{index + 1}"
        rows.append(
            _evidence(
                encounter_id=encounter_id,
                fact_type="ability_detail",
                fact_key=key,
                value=dict(raw),
                source=source,
                locator_suffix=f"ability-{key}",
                confidence="high",
                notes="Source ability retained for review; no canonical ability-detail mapping yet.",
            )
        )

    phases = payload.get("phases") if isinstance(payload.get("phases"), list) else []
    for index, raw in enumerate(phases):
        if isinstance(raw, dict):
            name = str(raw.get("name") or raw.get("phase") or f"phase_{index + 1}").strip()
            value: Any = dict(raw)
        else:
            name = f"phase_{index + 1}"
            value = raw
        rows.append(
            _evidence(
                encounter_id=encounter_id,
                fact_type="phase",
                fact_key=_slug(name) or f"phase_{index + 1}",
                value=value,
                source=source,
                locator_suffix=f"phase-{index + 1}",
                confidence="high",
            )
        )

    difficulty = payload.get("difficulty_notes")
    if isinstance(difficulty, dict) and any(difficulty.values()):
        rows.append(
            _evidence(
                encounter_id=encounter_id,
                fact_type="mechanic_detail",
                fact_key="difficulty_notes",
                value=difficulty,
                source=source,
                locator_suffix="difficulty-notes",
                confidence="high",
            )
        )

    return BossEncounterProjection(
        source_path=Path(source_path),
        content_id=content_id,
        encounter_id=encounter_id,
        encounter_name=encounter_name,
        evidence=tuple(rows),
        mechanic_count=len(mechanics),
        ability_count=len(abilities),
        phase_count=len(phases),
        inferred_mechanic_count=inferred,
        incomplete_mechanic_count=incomplete,
    )


def project_boss_file(path: Path) -> BossEncounterProjection:
    path = Path(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Boss source must be a JSON object: {path}")
    return project_boss_payload(payload, source_path=path)


def projection_to_packet(projection: BossEncounterProjection) -> dict[str, Any]:
    evidence = []
    for row in projection.evidence:
        evidence.append(
            {
                "fact_type": row.fact_type,
                "fact_key": row.fact_key,
                "value": row.value,
                "source_type": row.source_type,
                "source_name": row.source_name,
                "source_locator": row.source_locator,
                "source_revision": row.source_revision,
                "source_family": row.source_family,
                "game_update": row.game_update,
                "patch_version": row.patch_version,
                "confidence": row.confidence,
                "notes": row.notes,
            }
        )
    return {
        "schema_version": 1,
        "content_id": projection.content_id,
        "encounter_id": projection.encounter_id,
        "encounter_name": projection.encounter_name,
        "generated_from": str(projection.source_path),
        "evidence": evidence,
    }


def write_projection_packet(projection: BossEncounterProjection, output_path: Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(projection_to_packet(projection), ensure_ascii=False, indent=2) + "\n"
    if output_path.exists() and output_path.read_text(encoding="utf-8") == text:
        return output_path
    output_path.write_text(text, encoding="utf-8")
    return output_path
