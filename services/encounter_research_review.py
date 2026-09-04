from __future__ import annotations

"""Reviewer helpers for Encounter Research candidates.

This module deliberately edits only staged research state. Archived source files
and extracted evidence text remain immutable provenance, and no canonical ESO
encounter tables are touched here.
"""

from dataclasses import dataclass
import json
from pathlib import Path
import re

from services.encounter_research_store import (
    EncounterResearchCandidate,
    EncounterResearchSource,
    EncounterResearchStore,
    SUPPORTED_MAP_SUFFIXES,
)


_DATA_URL_RE = re.compile(
    r"data:image/[^;]+;base64,[A-Za-z0-9+/=\r\n]+",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class EncounterResearchSourcePreview:
    source_name: str
    stored_path: str
    source_type: str
    language: str
    text: str


def candidate_value_text(candidate: EncounterResearchCandidate) -> str:
    """Return a stable, human-editable JSON representation of a candidate value."""
    return json.dumps(candidate.value, indent=2, ensure_ascii=False, sort_keys=True)


def parse_candidate_value(text: str):
    """Parse reviewer-edited JSON while requiring a real JSON value."""
    raw = str(text or "").strip()
    if not raw:
        raise ValueError("Structured value must contain valid JSON")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Structured value is not valid JSON: line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc


def update_candidate_value(
    store: EncounterResearchStore,
    candidate_id: str,
    value,
) -> EncounterResearchCandidate:
    """Replace only the staged normalized value for one research candidate."""
    # Validate serializability before touching persistent state.
    try:
        json.dumps(value, ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Structured value is not JSON serializable: {exc}") from exc

    payload = store._load()
    for index, raw in enumerate(payload.get("candidates", [])):
        if str(raw.get("candidate_id", "")) != candidate_id:
            continue
        updated = dict(raw)
        updated["value"] = value
        payload["candidates"][index] = updated
        store._save(payload)
        return EncounterResearchCandidate(**updated)
    raise KeyError(f"Unknown encounter research candidate: {candidate_id}")


def _source_for_candidate(
    store: EncounterResearchStore,
    candidate: EncounterResearchCandidate,
) -> EncounterResearchSource | None:
    return next(
        (row for row in store.sources() if row.source_id == candidate.source_id),
        None,
    )


def candidate_source_preview(
    store: EncounterResearchStore,
    candidate_id: str,
    *,
    context_lines: int = 2,
    max_chars: int = 6000,
) -> EncounterResearchSourcePreview:
    """Return bounded source context around the immutable extracted evidence line."""
    candidate = next(
        (row for row in store.candidates() if row.candidate_id == candidate_id),
        None,
    )
    if candidate is None:
        raise KeyError(f"Unknown encounter research candidate: {candidate_id}")
    source = _source_for_candidate(store, candidate)
    if source is None:
        raise KeyError(f"Research source is missing for candidate: {candidate_id}")

    path = store.data_dir / Path(source.stored_path)
    if path.suffix.lower() in SUPPORTED_MAP_SUFFIXES:
        text = (
            f"Raid Map source: {source.original_name}\n"
            f"Stored at: {source.stored_path}\n"
            "Image content is preserved as a file; text extraction is not performed."
        )
        return EncounterResearchSourcePreview(
            source_name=source.original_name,
            stored_path=source.stored_path,
            source_type=source.source_type,
            language=source.language,
            text=text,
        )

    try:
        source_text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise OSError(f"Could not read research source {source.original_name}: {exc}") from exc
    source_text = _DATA_URL_RE.sub("[embedded image removed]", source_text)

    raw_lines = source_text.splitlines()
    normalized = [re.sub(r"\s+", " ", line).strip() for line in raw_lines]
    evidence = re.sub(r"\s+", " ", candidate.evidence_text).strip()
    match_index = next(
        (index for index, line in enumerate(normalized) if evidence and line == evidence),
        None,
    )

    if match_index is None:
        excerpt = candidate.evidence_text or "Source evidence line was not located in the archived text."
    else:
        start = max(0, match_index - max(0, int(context_lines)))
        end = min(len(raw_lines), match_index + max(0, int(context_lines)) + 1)
        excerpt_lines = []
        for index in range(start, end):
            marker = ">" if index == match_index else " "
            excerpt_lines.append(f"{marker} {index + 1}: {normalized[index]}")
        excerpt = "\n".join(excerpt_lines)

    if len(excerpt) > max_chars:
        excerpt = excerpt[: max(0, max_chars - 22)] + "\n[preview truncated]"

    return EncounterResearchSourcePreview(
        source_name=source.original_name,
        stored_path=source.stored_path,
        source_type=source.source_type,
        language=source.language,
        text=excerpt,
    )
