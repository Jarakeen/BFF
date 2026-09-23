from __future__ import annotations

"""Build a privacy-limited FoundryDock user database seed for a custom EXE.

This seed intentionally carries only raid-setup state:
- Personnel
- Teams and memberships
- Personnel assignments
- Saved Raid Plans
- Only the player/character/build records required by the selected Raid Plan

Achievement/collectible and other checklist progress is not copied.
"""

import argparse
import json
import sqlite3
from pathlib import Path


KEEP_TABLES = (
    "roster_member",
    "team",
    "team_member",
    "roster_member_assignment",
    "raid_plan",
    "build_catalog",
)


def _connect(path: Path) -> sqlite3.Connection:
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = OFF")
    return db


def _table_exists(db: sqlite3.Connection, table: str) -> bool:
    return db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone() is not None


def _copy_table(source: sqlite3.Connection, target: sqlite3.Connection, table: str) -> int:
    if not _table_exists(source, table):
        return 0
    schema = source.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    if schema is None or not str(schema["sql"] or "").strip():
        return 0
    target.execute(str(schema["sql"]))

    columns = [
        str(row["name"])
        for row in source.execute(f'PRAGMA table_info("{table}")').fetchall()
    ]
    if not columns:
        return 0
    quoted = ", ".join(f'"{column}"' for column in columns)
    rows = source.execute(f'SELECT {quoted} FROM "{table}"').fetchall()
    if rows:
        placeholders = ", ".join("?" for _ in columns)
        target.executemany(
            f'INSERT INTO "{table}" ({quoted}) VALUES ({placeholders})',
            [tuple(row[column] for column in columns) for row in rows],
        )
    return len(rows)


def _filter_build_catalog_for_selected_plan(target: sqlite3.Connection) -> int:
    if not _table_exists(target, "build_catalog") or not _table_exists(target, "raid_plan"):
        return 0
    catalog_row = target.execute(
        "SELECT payload_json FROM build_catalog WHERE singleton_id = 1"
    ).fetchone()
    plan_rows = target.execute(
        "SELECT payload_json FROM raid_plan ORDER BY updated_at DESC, plan_id COLLATE NOCASE"
    ).fetchall()
    if catalog_row is None or len(plan_rows) != 1:
        return 0

    catalog = json.loads(str(catalog_row["payload_json"] or "{}"))
    plan = json.loads(str(plan_rows[0]["payload_json"] or "{}"))
    members = [row for row in plan.get("members", []) if isinstance(row, dict)]

    player_ids = {str(row.get("player_id") or "").strip() for row in members}
    character_ids = {str(row.get("character_id") or "").strip() for row in members}
    build_ids = {str(row.get("selected_build_id") or "").strip() for row in members}
    gamertags = {str(row.get("gamertag") or "").strip().casefold() for row in members}
    character_names = {str(row.get("character_name") or "").strip().casefold() for row in members}
    selected_names = {str(row.get("selected_build_name") or "").strip().casefold() for row in members}
    player_ids.discard("")
    character_ids.discard("")
    build_ids.discard("")
    gamertags.discard("")
    character_names.discard("")
    selected_names.discard("")

    builds = []
    for build in catalog.get("builds", []):
        if not isinstance(build, dict):
            continue
        build_id = str(build.get("build_id") or "").strip()
        character_id = str(build.get("character_id") or "").strip()
        build_name = str(build.get("name") or "").strip().casefold()
        source = build.get("source") if isinstance(build.get("source"), dict) else {}
        source_plan_id = str(source.get("plan_id") or "").strip().casefold()
        if (
            build_id in build_ids
            or (source_plan_id and source_plan_id == str(plan.get("plan_id") or "").strip().casefold())
            or (build_name and build_name in selected_names and character_id in character_ids)
        ):
            builds.append(build)
            if build_id:
                build_ids.add(build_id)
            if character_id:
                character_ids.add(character_id)

    characters = []
    for character in catalog.get("characters", []):
        if not isinstance(character, dict):
            continue
        character_id = str(character.get("character_id") or "").strip()
        name = str(character.get("name") or "").strip().casefold()
        gamertag = str(character.get("gamertag") or "").strip().casefold()
        if character_id in character_ids or (
            name and name in character_names and (not gamertags or gamertag in gamertags)
        ):
            characters.append(character)
            if character_id:
                character_ids.add(character_id)
            player_id = str(character.get("player_id") or "").strip()
            if player_id:
                player_ids.add(player_id)

    players = [
        player for player in catalog.get("players", [])
        if isinstance(player, dict)
        and (
            str(player.get("player_id") or "").strip() in player_ids
            or str(player.get("gamertag") or "").strip().casefold() in gamertags
        )
    ]
    assignments = [
        row for row in catalog.get("team_assignments", [])
        if isinstance(row, dict)
        and str(row.get("build_id") or "").strip() in build_ids
    ]
    filtered = {
        "schema_version": int(catalog.get("schema_version") or 4),
        "players": players,
        "characters": characters,
        "builds": builds,
        "team_assignments": assignments,
    }
    target.execute(
        "UPDATE build_catalog SET payload_json = ?, updated_at = CURRENT_TIMESTAMP WHERE singleton_id = 1",
        (json.dumps(filtered, ensure_ascii=False, sort_keys=True),),
    )
    return len(builds)


def build_seed(
    source_path: Path,
    destination_path: Path,
    *,
    plan_id: str | None = None,
) -> dict[str, int]:
    source_path = Path(source_path)
    destination_path = Path(destination_path)
    if not source_path.is_file():
        raise FileNotFoundError(f"FoundryDock user database not found: {source_path}")

    destination_path.parent.mkdir(parents=True, exist_ok=True)
    if destination_path.exists():
        destination_path.unlink()

    source = _connect(source_path)
    target = _connect(destination_path)
    counts: dict[str, int] = {}
    try:
        for table in KEEP_TABLES:
            counts[table] = _copy_table(source, target, table)

        if _table_exists(target, "raid_plan"):
            selected_plan_id = str(plan_id or "").strip()
            plan_rows = target.execute(
                "SELECT plan_id FROM raid_plan ORDER BY updated_at DESC, plan_id COLLATE NOCASE"
            ).fetchall()
            if selected_plan_id:
                exists = any(
                    str(row["plan_id"]).casefold() == selected_plan_id.casefold()
                    for row in plan_rows
                )
                if not exists:
                    raise ValueError(
                        f"requested Raid Plan is not present in the user database: {selected_plan_id}"
                    )
                target.execute(
                    "DELETE FROM raid_plan WHERE plan_id <> ? COLLATE NOCASE",
                    (selected_plan_id,),
                )
                counts["raid_plan"] = 1
            elif len(plan_rows) > 1:
                raise ValueError(
                    "multiple saved Raid Plans exist; provide --plan-id so the custom EXE "
                    "does not accidentally include unrelated plans"
                )

        if _table_exists(target, "build_catalog"):
            counts["build_catalog"] = _filter_build_catalog_for_selected_plan(target)

        target.execute("PRAGMA foreign_keys = ON")
        violations = target.execute("PRAGMA foreign_key_check").fetchall()
        if violations:
            raise RuntimeError(
                "custom user database seed failed foreign-key validation: "
                + "; ".join(str(tuple(row)) for row in violations[:10])
            )
        target.commit()
    except Exception:
        target.rollback()
        target.close()
        source.close()
        destination_path.unlink(missing_ok=True)
        raise
    finally:
        try:
            source.close()
        except Exception:
            pass
        try:
            target.close()
        except Exception:
            pass
    return counts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--plan-id", default="")
    args = parser.parse_args()

    counts = build_seed(
        args.source,
        args.destination,
        plan_id=args.plan_id or None,
    )
    print(f"Created custom FoundryDock user seed: {args.destination}")
    for table in KEEP_TABLES:
        print(f"{table}: {counts.get(table, 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
