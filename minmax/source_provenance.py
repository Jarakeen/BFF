from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


DEFAULT_SOURCE_MANIFEST = (
    Path(__file__).resolve().parents[1] / "data" / "source_manifest.json"
)


class SourceProvenanceError(ValueError):
    """Raised when source provenance metadata is missing or malformed."""


@dataclass(frozen=True)
class SourceProvenance:
    key: str
    artifact: str
    source_system: str
    source_kind: str
    export_url: str
    export_table: str
    documentation_url: str
    documentation_revision_id: int | None
    record_count: int | None
    retrieved_at: str | None
    game_update: str | None
    api_version: str | None
    provenance_status: str
    derivation: str
    notes: tuple[str, ...]


def load_source_provenance(
    key: str,
    manifest_path: str | Path = DEFAULT_SOURCE_MANIFEST,
) -> SourceProvenance:
    """Load one explicit source record without inventing missing version data."""

    path = Path(manifest_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    sources = payload.get("sources")
    if not isinstance(sources, dict):
        raise SourceProvenanceError(
            f"Source manifest has no 'sources' object: {path}"
        )

    raw = sources.get(key)
    if not isinstance(raw, dict):
        raise SourceProvenanceError(
            f"Source provenance entry not found: {key}"
        )

    def required_text(field: str) -> str:
        value = raw.get(field)
        if not isinstance(value, str) or not value.strip():
            raise SourceProvenanceError(
                f"Source provenance {key!r} requires {field!r}"
            )
        return value.strip()

    def optional_text(field: str) -> str | None:
        value = raw.get(field)
        if value is None:
            return None
        if not isinstance(value, str):
            raise SourceProvenanceError(
                f"Source provenance {key!r} field {field!r} must be text or null"
            )
        return value.strip() or None

    notes = raw.get("notes", [])
    if not isinstance(notes, list) or not all(
        isinstance(note, str) for note in notes
    ):
        raise SourceProvenanceError(
            f"Source provenance {key!r} field 'notes' must be a string list"
        )

    documentation_revision_id = raw.get("documentation_revision_id")
    if documentation_revision_id is not None:
        documentation_revision_id = int(documentation_revision_id)

    record_count = raw.get("record_count")
    if record_count is not None:
        record_count = int(record_count)

    return SourceProvenance(
        key=key,
        artifact=required_text("artifact"),
        source_system=required_text("source_system"),
        source_kind=required_text("source_kind"),
        export_url=required_text("export_url"),
        export_table=required_text("export_table"),
        documentation_url=required_text("documentation_url"),
        documentation_revision_id=documentation_revision_id,
        record_count=record_count,
        retrieved_at=optional_text("retrieved_at"),
        game_update=optional_text("game_update"),
        api_version=optional_text("api_version"),
        provenance_status=required_text("provenance_status"),
        derivation=required_text("derivation"),
        notes=tuple(note.strip() for note in notes if note.strip()),
    )
