from __future__ import annotations

"""Local provenance for explicit Finch shared-snapshot copies.

This sidecar records which remote snapshot version produced a local copy. It does not
make Finch authoritative and does not track local edits. Freshness therefore means
"Finch changed since the snapshot you copied", never "remote is newer than your local
work".
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path

from services.finch_api_client import FinchSharedSnapshot


_SCHEMA_VERSION = 1


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _parse_timestamp(value: object) -> datetime | None:
    text = _clean(value)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def format_shared_timestamp(value: object) -> str:
    parsed = _parse_timestamp(value)
    if parsed is None:
        return _clean(value) or "Unknown time"
    return parsed.strftime("%Y-%m-%d %H:%M UTC")


@dataclass(frozen=True, slots=True)
class FinchCopyProvenance:
    kind: str
    snapshot_key: str
    local_key: str
    published_by: str
    source_updated_at: str
    copied_at: str


class FinchSharedProvenanceService:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def _load(self) -> tuple[FinchCopyProvenance, ...]:
        if not self.path.exists():
            return ()
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return ()
        if not isinstance(raw, dict) or raw.get("schema_version") != _SCHEMA_VERSION:
            return ()
        rows = raw.get("copies")
        if not isinstance(rows, list):
            return ()
        result = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            try:
                result.append(
                    FinchCopyProvenance(
                        kind=_clean(row.get("kind")),
                        snapshot_key=_clean(row.get("snapshot_key")),
                        local_key=_clean(row.get("local_key")),
                        published_by=_clean(row.get("published_by")),
                        source_updated_at=_clean(row.get("source_updated_at")),
                        copied_at=_clean(row.get("copied_at")),
                    )
                )
            except Exception:
                continue
        return tuple(result)

    def record_copy(
        self,
        *,
        snapshot: FinchSharedSnapshot,
        local_key: str,
    ) -> FinchCopyProvenance:
        row = FinchCopyProvenance(
            kind=_clean(snapshot.kind),
            snapshot_key=_clean(snapshot.snapshot_key),
            local_key=_clean(local_key),
            published_by=_clean(snapshot.published_by),
            source_updated_at=_clean(snapshot.updated_at),
            copied_at=datetime.now(timezone.utc).isoformat(),
        )
        existing = [
            item
            for item in self._load()
            if not (
                item.kind.casefold() == row.kind.casefold()
                and item.local_key.casefold() == row.local_key.casefold()
            )
        ]
        existing.append(row)
        payload = {
            "schema_version": _SCHEMA_VERSION,
            "copies": [asdict(item) for item in existing],
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return row

    def copies_for(
        self,
        *,
        kind: str,
        snapshot_key: str,
    ) -> tuple[FinchCopyProvenance, ...]:
        wanted_kind = _clean(kind).casefold()
        wanted_key = _clean(snapshot_key).casefold()
        return tuple(
            row
            for row in self._load()
            if row.kind.casefold() == wanted_kind
            and row.snapshot_key.casefold() == wanted_key
        )

    def latest_copy_for(
        self,
        *,
        kind: str,
        snapshot_key: str,
    ) -> FinchCopyProvenance | None:
        copies = self.copies_for(kind=kind, snapshot_key=snapshot_key)
        if not copies:
            return None
        return max(
            copies,
            key=lambda row: _parse_timestamp(row.copied_at)
            or datetime.min.replace(tzinfo=timezone.utc),
        )

    def relation_for(self, snapshot: FinchSharedSnapshot) -> str:
        newest_copy = self.latest_copy_for(
            kind=snapshot.kind,
            snapshot_key=snapshot.snapshot_key,
        )
        if newest_copy is None:
            return "Not copied locally"
        remote_time = _parse_timestamp(snapshot.updated_at)
        copied_source_time = _parse_timestamp(newest_copy.source_updated_at)
        if remote_time is not None and copied_source_time is not None:
            if remote_time > copied_source_time:
                return f"Updated on Finch since copy • local: {newest_copy.local_key}"
            if remote_time < copied_source_time:
                return f"Local copy came from a newer Finch snapshot • {newest_copy.local_key}"
        return f"Copied from this Finch snapshot • local: {newest_copy.local_key}"


__all__ = [
    "FinchCopyProvenance",
    "FinchSharedProvenanceService",
    "format_shared_timestamp",
]
