from __future__ import annotations

"""Build canonical encounter bootstrap plans from reviewed evidence packets."""

import json
from pathlib import Path
import re
import sqlite3

from services.encounter_bootstrap import EncounterBootstrapPlan


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


def build_encounter_bootstrap_plan_from_evidence(
    connection: sqlite3.Connection,
    packet_path: Path,
) -> EncounterBootstrapPlan:
    packet_path = Path(packet_path)
    payload = json.loads(packet_path.read_text(encoding="utf-8"))

    encounter_id = str(payload.get("encounter_id") or "").strip()
    encounter_name = str(payload.get("encounter_name") or "").strip()
    content_id = str(payload.get("content_id") or "").strip()

    if not encounter_id:
        raise RuntimeError("Encounter evidence packet has no encounter_id")
    if not encounter_name:
        raise RuntimeError("Encounter evidence packet has no encounter_name")
    if not content_id:
        raise RuntimeError("Encounter evidence packet has no content_id")

    content = connection.execute(
        "SELECT 1 FROM content WHERE id = ?",
        (content_id,),
    ).fetchone()
    if content is None:
        raise RuntimeError(f"Content row does not exist: {content_id!r}")

    return EncounterBootstrapPlan(
        encounter_id=encounter_id,
        legacy_boss_id="",
        bootstrap_source="encounter_evidence_packet",
        source_record=str(packet_path),
        content_id=content_id,
        name=encounter_name,
        slug=_slugify(encounter_name),
        summary="",
        location="",
        species="",
        reaction="",
        source_url="",
        source_page_title=f"Encounter evidence packet: {packet_path.name}",
        source_revision_id="",
        retrieved_at="",
        source_license="",
    )
