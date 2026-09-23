from __future__ import annotations

"""Create a minimal canonical build catalog for one seeded Raid Plan."""

import argparse
import json
import sqlite3
from pathlib import Path

from services.build_catalog_service import BuildCatalogService


def _load_selected_plan(database_path: Path, plan_id: str | None) -> dict:
    db = sqlite3.connect(database_path)
    db.row_factory = sqlite3.Row
    try:
        rows = db.execute(
            "SELECT plan_id, payload_json FROM raid_plan ORDER BY updated_at DESC, plan_id COLLATE NOCASE"
        ).fetchall()
    finally:
        db.close()
    if not rows:
        return {}
    wanted = str(plan_id or "").strip().casefold()
    if wanted:
        row = next((row for row in rows if str(row["plan_id"]).casefold() == wanted), None)
        if row is None:
            raise ValueError(f"Raid Plan not found in seed database: {plan_id}")
    elif len(rows) == 1:
        row = rows[0]
    else:
        raise ValueError("multiple Raid Plans exist in seed database; select one")
    return json.loads(str(row["payload_json"] or "{}"))


def build_plan_catalog(
    source_catalog: Path,
    seed_database: Path,
    destination_catalog: Path,
    *,
    plan_id: str | None = None,
) -> dict[str, int]:
    source_catalog = Path(source_catalog)
    destination_catalog = Path(destination_catalog)
    if not source_catalog.is_file():
        destination_catalog.parent.mkdir(parents=True, exist_ok=True)
        BuildCatalogService(destination_catalog).save({})
        return {"players": 0, "characters": 0, "builds": 0, "team_assignments": 0}

    catalog = BuildCatalogService(source_catalog).load()
    plan = _load_selected_plan(Path(seed_database), plan_id)
    members = [row for row in plan.get("members", []) if isinstance(row, dict)]

    player_ids = {str(row.get("player_id") or "").strip() for row in members}
    character_ids = {str(row.get("character_id") or "").strip() for row in members}
    build_ids = {str(row.get("selected_build_id") or "").strip() for row in members}
    gamertags = {str(row.get("gamertag") or "").strip().casefold() for row in members}
    character_names = {
        str(row.get("character_name") or "").strip().casefold() for row in members
    }
    selected_names = {
        str(row.get("selected_build_name") or "").strip().casefold() for row in members
    }
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
        build_character_id = str(build.get("character_id") or "").strip()
        build_name = str(build.get("name") or "").strip().casefold()
        source = build.get("source") if isinstance(build.get("source"), dict) else {}
        source_plan_id = str(source.get("plan_id") or "").strip().casefold()
        selected = (
            build_id in build_ids
            or (source_plan_id and source_plan_id == str(plan.get("plan_id") or "").strip().casefold())
            or (build_name and build_name in selected_names and build_character_id in character_ids)
        )
        if not selected:
            continue
        builds.append(build)
        if build_character_id:
            character_ids.add(build_character_id)
        if build_id:
            build_ids.add(build_id)

    characters = []
    for character in catalog.get("characters", []):
        if not isinstance(character, dict):
            continue
        character_id = str(character.get("character_id") or "").strip()
        name = str(character.get("name") or "").strip().casefold()
        gamertag = str(character.get("gamertag") or "").strip().casefold()
        selected = (
            character_id in character_ids
            or (name and name in character_names and (not gamertags or gamertag in gamertags))
        )
        if not selected:
            continue
        characters.append(character)
        if character_id:
            character_ids.add(character_id)
        player_id = str(character.get("player_id") or "").strip()
        if player_id:
            player_ids.add(player_id)

    players = []
    for player in catalog.get("players", []):
        if not isinstance(player, dict):
            continue
        player_id = str(player.get("player_id") or "").strip()
        gamertag = str(player.get("gamertag") or "").strip().casefold()
        if player_id in player_ids or (gamertag and gamertag in gamertags):
            players.append(player)
            if player_id:
                player_ids.add(player_id)

    assignments = [
        row
        for row in catalog.get("team_assignments", [])
        if isinstance(row, dict)
        and str(row.get("build_id") or "").strip() in build_ids
    ]

    output = {
        "schema_version": 4,
        "players": players,
        "characters": characters,
        "builds": builds,
        "team_assignments": assignments,
    }
    destination_catalog.parent.mkdir(parents=True, exist_ok=True)
    BuildCatalogService(destination_catalog).save(output)
    return {key: len(output[key]) for key in ("players", "characters", "builds", "team_assignments")}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-catalog", type=Path, required=True)
    parser.add_argument("--seed-database", type=Path, required=True)
    parser.add_argument("--destination-catalog", type=Path, required=True)
    parser.add_argument("--plan-id", default="")
    args = parser.parse_args()
    counts = build_plan_catalog(
        args.source_catalog,
        args.seed_database,
        args.destination_catalog,
        plan_id=args.plan_id or None,
    )
    print(f"Created Raid Plan build catalog: {args.destination_catalog}")
    for key, value in counts.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
