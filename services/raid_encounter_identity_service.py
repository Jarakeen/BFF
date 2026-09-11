from __future__ import annotations

"""Reviewed raid-planning encounter identities.

This service groups raw persisted encounter records into the fight units a raid lead
actually plans. It is identity/presentation metadata only: it does not create or
replace canonical mechanic truth.
"""

from dataclasses import dataclass
import json
from pathlib import Path


class RaidEncounterIdentityError(RuntimeError):
    pass


@dataclass(frozen=True)
class RaidEncounterIdentity:
    content_id: str
    content_name: str
    encounter_id: str
    display_name: str
    member_ids: tuple[str, ...]

    @property
    def is_grouped(self) -> bool:
        return len(self.member_ids) > 1 or self.encounter_id not in self.member_ids

    @property
    def primary_member_id(self) -> str:
        return self.member_ids[0]


def _text(value: object, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise RaidEncounterIdentityError(f"raid encounter identity field {field!r} must be non-empty")
    return text


def load_raid_encounter_identities(data_root: Path) -> tuple[RaidEncounterIdentity, ...]:
    path = Path(data_root) / "raid_encounter_identity.json"
    if not path.exists():
        return ()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RaidEncounterIdentityError(f"Could not load {path}: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise RaidEncounterIdentityError("raid_encounter_identity.json must use schema_version 1")
    rows = payload.get("encounters")
    if not isinstance(rows, list):
        raise RaidEncounterIdentityError("raid_encounter_identity.json encounters must be a list")

    result: list[RaidEncounterIdentity] = []
    seen: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise RaidEncounterIdentityError(f"encounters[{index}] must be an object")
        encounter_id = _text(row.get("encounter_id"), "encounter_id")
        if encounter_id in seen:
            raise RaidEncounterIdentityError(f"duplicate raid encounter id {encounter_id!r}")
        raw_members = row.get("member_ids")
        if not isinstance(raw_members, list) or not raw_members:
            raise RaidEncounterIdentityError(f"{encounter_id}: member_ids must be a non-empty list")
        member_ids = tuple(_text(value, "member_ids") for value in raw_members)
        if len(set(member_ids)) != len(member_ids):
            raise RaidEncounterIdentityError(f"{encounter_id}: member_ids must be unique")
        seen.add(encounter_id)
        result.append(
            RaidEncounterIdentity(
                content_id=_text(row.get("content_id"), "content_id"),
                content_name=_text(row.get("content_name"), "content_name"),
                encounter_id=encounter_id,
                display_name=_text(row.get("display_name"), "display_name"),
                member_ids=member_ids,
            )
        )

    return tuple(
        sorted(
            result,
            key=lambda row: (
                row.content_name.casefold(),
                row.display_name.casefold(),
                row.encounter_id,
            ),
        )
    )


def raid_encounters_for_content(
    data_root: Path,
    content_name_or_id: str,
) -> tuple[RaidEncounterIdentity, ...]:
    target = str(content_name_or_id or "").strip().casefold()
    if not target:
        return ()
    return tuple(
        row
        for row in load_raid_encounter_identities(data_root)
        if row.content_id.casefold() == target or row.content_name.casefold() == target
    )


__all__ = [
    "RaidEncounterIdentity",
    "RaidEncounterIdentityError",
    "load_raid_encounter_identities",
    "raid_encounters_for_content",
]
