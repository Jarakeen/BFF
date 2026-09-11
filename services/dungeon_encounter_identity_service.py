from __future__ import annotations

"""Reviewed dungeon-planning encounter identities.

This service groups raw persisted dungeon records into the fight units a group
actually plans. It is identity/presentation metadata only and does not create or
replace canonical mechanic truth.
"""

from dataclasses import dataclass
import json
from pathlib import Path


class DungeonEncounterIdentityError(RuntimeError):
    pass


@dataclass(frozen=True)
class DungeonEncounterIdentity:
    content_id: str
    content_name: str
    release_year: int
    release_update: int
    release_pack: str
    encounter_id: str
    display_name: str
    member_ids: tuple[str, ...]

    @property
    def is_grouped(self) -> bool:
        return len(self.member_ids) > 1 or self.encounter_id not in self.member_ids

    @property
    def primary_member_id(self) -> str:
        return self.member_ids[0]

    @property
    def release_key(self) -> tuple[int, int]:
        return (self.release_year, self.release_update)


def _text(value: object, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise DungeonEncounterIdentityError(
            f"dungeon encounter identity field {field!r} must be non-empty"
        )
    return text


def _positive_int(value: object, field: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise DungeonEncounterIdentityError(
            f"dungeon encounter identity field {field!r} must be an integer"
        ) from exc
    if number <= 0:
        raise DungeonEncounterIdentityError(
            f"dungeon encounter identity field {field!r} must be positive"
        )
    return number


def load_dungeon_encounter_identities(
    data_root: Path,
) -> tuple[DungeonEncounterIdentity, ...]:
    path = Path(data_root) / "dungeon_encounter_identity.json"
    if not path.exists():
        return ()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DungeonEncounterIdentityError(f"Could not load {path}: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise DungeonEncounterIdentityError(
            "dungeon_encounter_identity.json must use schema_version 1"
        )
    rows = payload.get("encounters")
    if not isinstance(rows, list):
        raise DungeonEncounterIdentityError(
            "dungeon_encounter_identity.json encounters must be a list"
        )

    result: list[DungeonEncounterIdentity] = []
    seen: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise DungeonEncounterIdentityError(f"encounters[{index}] must be an object")
        encounter_id = _text(row.get("encounter_id"), "encounter_id")
        if encounter_id in seen:
            raise DungeonEncounterIdentityError(
                f"duplicate dungeon encounter id {encounter_id!r}"
            )
        raw_members = row.get("member_ids")
        if not isinstance(raw_members, list) or not raw_members:
            raise DungeonEncounterIdentityError(
                f"{encounter_id}: member_ids must be a non-empty list"
            )
        member_ids = tuple(_text(value, "member_ids") for value in raw_members)
        if len(set(member_ids)) != len(member_ids):
            raise DungeonEncounterIdentityError(
                f"{encounter_id}: member_ids must be unique"
            )
        seen.add(encounter_id)
        result.append(
            DungeonEncounterIdentity(
                content_id=_text(row.get("content_id"), "content_id"),
                content_name=_text(row.get("content_name"), "content_name"),
                release_year=_positive_int(row.get("release_year"), "release_year"),
                release_update=_positive_int(
                    row.get("release_update"), "release_update"
                ),
                release_pack=_text(row.get("release_pack"), "release_pack"),
                encounter_id=encounter_id,
                display_name=_text(row.get("display_name"), "display_name"),
                member_ids=member_ids,
            )
        )

    return tuple(
        sorted(
            result,
            key=lambda row: (
                -row.release_year,
                -row.release_update,
                row.content_name.casefold(),
                row.display_name.casefold(),
                row.encounter_id,
            ),
        )
    )


def dungeon_encounters_for_content(
    data_root: Path,
    content_name_or_id: str,
) -> tuple[DungeonEncounterIdentity, ...]:
    target = str(content_name_or_id or "").strip().casefold()
    if not target:
        return ()
    return tuple(
        row
        for row in load_dungeon_encounter_identities(data_root)
        if row.content_id.casefold() == target or row.content_name.casefold() == target
    )


__all__ = [
    "DungeonEncounterIdentity",
    "DungeonEncounterIdentityError",
    "dungeon_encounters_for_content",
    "load_dungeon_encounter_identities",
]
