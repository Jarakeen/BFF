from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
from typing import Any


_SPATIAL_EXACT_KEYS = {
    "x",
    "y",
    "z",
    "posx",
    "posy",
    "posz",
    "positionx",
    "positiony",
    "positionz",
}
_SPATIAL_TOKENS = (
    "position",
    "coordinate",
    "location",
    "distance",
    "range",
    "radius",
    "width",
    "angle",
    "facing",
    "heading",
)


@dataclass(frozen=True)
class RotationDDPeriodicEsoLogsRawSpatialMetadataField:
    path: str
    rendered_values: tuple[str, ...]
    occurrence_count: int


@dataclass(frozen=True)
class RotationDDPeriodicEsoLogsRawSpatialMetadataReport:
    ability_id: int
    event_count: int
    target_actor_count: int
    fields: tuple[RotationDDPeriodicEsoLogsRawSpatialMetadataField, ...]
    unresolved: tuple[str, ...] = ()


class RotationDDPeriodicEsoLogsRawSpatialMetadataService:
    """Inventory spatial/range-like keys preserved in raw ESO Logs event JSON.

    Evidence only. This service deliberately does not interpret a matching raw field as
    authoritative coordinates, range, radius, or hitbox geometry. It reports exactly
    which potentially spatial keys survived import for one observed ability id so a
    mechanic review can decide whether the data is usable.
    """

    def __init__(self, logs_database_path: str | Path) -> None:
        self.logs_database_path = Path(logs_database_path)

    def inspect(
        self,
        ability_id: int,
        *,
        max_values_per_field: int = 12,
    ) -> RotationDDPeriodicEsoLogsRawSpatialMetadataReport:
        requested = int(ability_id)
        if requested <= 0:
            raise ValueError("ability_id must be positive")
        if not self.logs_database_path.is_file():
            return RotationDDPeriodicEsoLogsRawSpatialMetadataReport(
                ability_id=requested,
                event_count=0,
                target_actor_count=0,
                fields=(),
                unresolved=(f"ESO Logs database not found: {self.logs_database_path}",),
            )

        with sqlite3.connect(
            f"file:{self.logs_database_path.resolve().as_posix()}?mode=ro",
            uri=True,
        ) as db:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA query_only = ON")
            columns = {str(row[1]) for row in db.execute("PRAGMA table_info(log_event)")}
            required = {
                "report_code",
                "fight_id",
                "target_id",
                "ability_game_id",
                "raw_json",
            }
            missing = sorted(required - columns)
            if missing:
                return RotationDDPeriodicEsoLogsRawSpatialMetadataReport(
                    ability_id=requested,
                    event_count=0,
                    target_actor_count=0,
                    fields=(),
                    unresolved=(
                        "log_event is missing required columns: " + ", ".join(missing),
                    ),
                )
            rows = db.execute(
                """
                SELECT report_code, fight_id, target_id, raw_json
                FROM log_event
                WHERE ability_game_id = ?
                ORDER BY report_code, fight_id, target_id
                """,
                (requested,),
            ).fetchall()

        target_keys = {
            (str(row["report_code"]), int(row["fight_id"]), int(row["target_id"]))
            for row in rows
            if row["target_id"] is not None
        }
        counts: dict[str, Counter[str]] = {}
        for row in rows:
            raw = str(row["raw_json"] or "").strip()
            if not raw:
                continue
            try:
                payload = json.loads(raw)
            except (TypeError, json.JSONDecodeError):
                continue
            self._collect(payload, path="", counts=counts)

        fields = tuple(
            RotationDDPeriodicEsoLogsRawSpatialMetadataField(
                path=path,
                rendered_values=tuple(
                    value
                    for value, _count in counter.most_common(
                        max(1, int(max_values_per_field))
                    )
                ),
                occurrence_count=sum(counter.values()),
            )
            for path, counter in sorted(counts.items(), key=lambda item: item[0].casefold())
        )
        unresolved: list[str] = []
        if rows and not fields:
            unresolved.append(
                "raw event JSON exposes no position/coordinate/location/distance/range/"
                "radius/width/angle/facing/heading-like metadata keys"
            )
        return RotationDDPeriodicEsoLogsRawSpatialMetadataReport(
            ability_id=requested,
            event_count=len(rows),
            target_actor_count=len(target_keys),
            fields=fields,
            unresolved=tuple(unresolved),
        )

    @classmethod
    def _collect(
        cls,
        value: Any,
        *,
        path: str,
        counts: dict[str, Counter[str]],
    ) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                key_text = str(key)
                child_path = f"{path}.{key_text}" if path else key_text
                normalized = "".join(
                    character
                    for character in key_text.casefold()
                    if character.isalnum()
                )
                if (
                    normalized in _SPATIAL_EXACT_KEYS
                    or any(token in normalized for token in _SPATIAL_TOKENS)
                ):
                    rendered = cls._render(child)
                    counts.setdefault(child_path, Counter())[rendered] += 1
                cls._collect(child, path=child_path, counts=counts)
        elif isinstance(value, list):
            for child in value:
                cls._collect(
                    child,
                    path=f"{path}[]" if path else "[]",
                    counts=counts,
                )

    @staticmethod
    def _render(value: Any) -> str:
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False, sort_keys=True)
        return json.dumps(value, ensure_ascii=False)


__all__ = [
    "RotationDDPeriodicEsoLogsRawSpatialMetadataField",
    "RotationDDPeriodicEsoLogsRawSpatialMetadataReport",
    "RotationDDPeriodicEsoLogsRawSpatialMetadataService",
]
