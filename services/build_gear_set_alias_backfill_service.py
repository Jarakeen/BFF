from __future__ import annotations

"""One-time/idempotent repair for gear shorthand stored by older roster imports.

The repair is intentionally narrow: only values recognized by the shared roster
alias registry are changed. Full canonical set names are left alone, including an
explicitly saved non-Perfected set. This lets old imported ``RO``/``Pill``/``SoB``
style values receive the same canonical/Perfected resolution as new imports
without rewriting unrelated build data.
"""

from dataclasses import dataclass
import json
from pathlib import Path
import shutil
from typing import Any

from services.roster_gear_set_alias_service import resolve_roster_gear_set_name


@dataclass(frozen=True)
class BuildGearAliasChange:
    build_name: str
    character_name: str
    field_path: str
    before: str
    after: str


@dataclass(frozen=True)
class BuildGearAliasBackfillReport:
    changed_values: int
    changed_builds: int
    backup_path: Path | None
    changes: tuple[BuildGearAliasChange, ...] = ()


def _build_label(member: dict[str, Any]) -> tuple[str, str]:
    return (
        str(member.get("BuildName") or "").strip(),
        str(member.get("Name") or "").strip(),
    )


def _repair_node(
    node: Any,
    *,
    database_path: Path,
    build_name: str,
    character_name: str,
    path: str,
    changes: list[BuildGearAliasChange],
) -> None:
    if isinstance(node, dict):
        for key, value in list(node.items()):
            child_path = f"{path}.{key}" if path else str(key)
            if key in {"Set", "Set2"} and isinstance(value, str) and value.strip():
                resolution = resolve_roster_gear_set_name(
                    value,
                    database_path=database_path,
                    aliases_only=True,
                )
                if resolution.matched_alias and resolution.changed:
                    node[key] = resolution.canonical_name
                    changes.append(
                        BuildGearAliasChange(
                            build_name=build_name,
                            character_name=character_name,
                            field_path=child_path,
                            before=value,
                            after=resolution.canonical_name,
                        )
                    )
                continue
            _repair_node(
                value,
                database_path=database_path,
                build_name=build_name,
                character_name=character_name,
                path=child_path,
                changes=changes,
            )
        return

    if isinstance(node, list):
        for index, value in enumerate(node):
            child_path = f"{path}[{index}]" if path else f"[{index}]"
            _repair_node(
                value,
                database_path=database_path,
                build_name=build_name,
                character_name=character_name,
                path=child_path,
                changes=changes,
            )


def backfill_saved_build_gear_aliases(
    builds_path: str | Path,
    database_path: str | Path,
    *,
    create_backup: bool = True,
) -> BuildGearAliasBackfillReport:
    builds_path = Path(builds_path)
    database_path = Path(database_path)
    if not builds_path.exists():
        return BuildGearAliasBackfillReport(0, 0, None, ())

    payload = json.loads(builds_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return BuildGearAliasBackfillReport(0, 0, None, ())

    members = payload.get("Members")
    if not isinstance(members, list):
        return BuildGearAliasBackfillReport(0, 0, None, ())

    changes: list[BuildGearAliasChange] = []
    for index, member in enumerate(members):
        if not isinstance(member, dict):
            continue
        build_name, character_name = _build_label(member)
        _repair_node(
            member,
            database_path=database_path,
            build_name=build_name,
            character_name=character_name,
            path=f"Members[{index}]",
            changes=changes,
        )

    if not changes:
        return BuildGearAliasBackfillReport(0, 0, None, ())

    backup_path: Path | None = None
    if create_backup:
        backup_path = builds_path.with_name(f"{builds_path.stem}.before-gear-alias-backfill{builds_path.suffix}")
        if not backup_path.exists():
            shutil.copy2(builds_path, backup_path)

    builds_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    changed_builds = len(
        {
            (change.character_name.casefold(), change.build_name.casefold())
            for change in changes
        }
    )
    return BuildGearAliasBackfillReport(
        changed_values=len(changes),
        changed_builds=changed_builds,
        backup_path=backup_path,
        changes=tuple(changes),
    )


__all__ = [
    "BuildGearAliasChange",
    "BuildGearAliasBackfillReport",
    "backfill_saved_build_gear_aliases",
]
