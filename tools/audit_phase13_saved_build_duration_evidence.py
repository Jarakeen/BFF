from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.skill_coefficient_repository import SkillCoefficientRepository
from models.build_model import PlayerBuild


def _load_build(path: Path, build_name: str, character_name: str | None = None) -> PlayerBuild:
    payload = json.loads(path.read_text(encoding="utf-8"))
    members = payload.get("Members", [])
    target_build = str(build_name or "").strip().casefold()
    target_character = str(character_name or "").strip().casefold()

    matches: list[PlayerBuild] = []
    for member in members:
        candidate_build = str(member.get("BuildName", "") or "").strip()
        candidate_character = str(member.get("Name", "") or "").strip()
        if candidate_build.casefold() != target_build:
            continue
        if target_character and candidate_character.casefold() != target_character:
            continue
        matches.append(PlayerBuild.from_dict(member))

    if not matches:
        raise ValueError(
            f"Saved build not found: character={character_name!r} build={build_name!r}"
        )
    if len(matches) > 1:
        raise ValueError(
            f"Saved build name is ambiguous: {build_name!r}; supply --character"
        )
    return matches[0]


def _ordinary_skills(build: PlayerBuild) -> tuple[tuple[str, int, str], ...]:
    rows: list[tuple[str, int, str]] = []
    for bar, values in (
        ("front", getattr(build, "FrontBarSkills", [])),
        ("back", getattr(build, "BackBarSkills", [])),
    ):
        for index, raw in enumerate(list(values or [])[:5], start=1):
            name = str(raw or "").strip()
            if name:
                rows.append((bar, index, name))
    return tuple(rows)


def _columns(connection: sqlite3.Connection, table: str) -> tuple[str, ...]:
    return tuple(str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})"))


def _clean(value) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit canonical duration evidence for one real saved build"
    )
    parser.add_argument("--build", required=True)
    parser.add_argument("--character")
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    parser.add_argument("--builds", default=str(ROOT / "data" / "builds.json"))
    args = parser.parse_args()

    database = Path(args.database)
    build = _load_build(Path(args.builds), args.build, args.character)
    skills = SkillCoefficientRepository(database)

    print("=" * 68)
    print(" PHASE 13 SAVED-BUILD DURATION EVIDENCE AUDIT")
    print("=" * 68)
    print(f"Character: {getattr(build, 'Name', '') or getattr(build, 'CharacterName', '')}")
    print(f"Build:     {getattr(build, 'BuildName', '')}")
    print(f"Database:  {database}")
    print("Boundary:  diagnostic only; no duration is inferred from tooltip wording")
    print()

    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        tables = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }

        timing_tables: list[tuple[str, tuple[str, ...]]] = []
        timing_tokens = ("duration", "tick", "interval", "cadence", "time")
        for table in sorted(tables):
            columns = _columns(connection, table)
            if "skill_rank_id" not in columns:
                continue
            interesting = tuple(
                column
                for column in columns
                if any(token in column.casefold() for token in timing_tokens)
            )
            if interesting:
                timing_tables.append((table, columns))

        for bar, slot, requested in _ordinary_skills(build):
            print(f"[{bar.upper()} {slot}] {requested}")
            print("-" * (len(requested) + 10))
            identity = skills.resolve_name(requested)
            rank = identity.rank
            if rank is None:
                print("resolution: unresolved")
                for item in identity.unresolved:
                    print(f"  unresolved: {item}")
                print()
                continue

            print(f"resolved name:   {rank.name}")
            print(f"skill_rank_id:   {rank.skill_rank_id}")
            print(f"ability_id:      {rank.ability_id}")
            print(f"base_ability_id: {rank.base_ability_id}")
            if identity.unresolved:
                for item in identity.unresolved:
                    print(f"  resolution note: {item}")

            rank_row = connection.execute(
                """
                SELECT duration, start_time, tick_time, cooldown, cast_time, channel_time,
                       raw_name, raw_description, raw_tooltip, coef_description
                FROM skill_rank
                WHERE id = ?
                """,
                (rank.skill_rank_id,),
            ).fetchone()
            if rank_row is not None:
                print(f"skill_rank.duration:    {rank_row['duration']}")
                print(f"skill_rank.start_time:  {rank_row['start_time']}")
                print(f"skill_rank.tick_time:   {rank_row['tick_time']}")
                print(f"skill_rank.cooldown:    {rank_row['cooldown']}")
                print(f"skill_rank.cast_time:   {rank_row['cast_time']}")
                print(f"skill_rank.channel:     {rank_row['channel_time']}")
                for label, key in (
                    ("rank description", "raw_description"),
                    ("rank tooltip", "raw_tooltip"),
                    ("coef description", "coef_description"),
                ):
                    value = _clean(rank_row[key])
                    if value:
                        print(f"{label}: {value}")

            if "ability" in tables:
                ability_columns = set(_columns(connection, "ability"))
                select = [
                    column
                    for column in (
                        "ability_id",
                        "name",
                        "duration",
                        "start_time",
                        "tick_time",
                        "cooldown",
                        "cast_time",
                        "channel_time",
                        "description",
                        "raw_description",
                        "raw_tooltip",
                        "coef_description",
                    )
                    if column in ability_columns
                ]
                row = connection.execute(
                    f"SELECT {', '.join(select)} FROM ability WHERE ability_id = ?",
                    (rank.ability_id,),
                ).fetchone()
                if row is not None:
                    print("ability row:")
                    for key in select:
                        value = row[key]
                        if value in (None, ""):
                            continue
                        rendered = _clean(value) if isinstance(value, str) else value
                        print(f"  {key}: {rendered}")

            found_component_timing = False
            for table, columns in timing_tables:
                selected = ["skill_rank_id"]
                for column in columns:
                    if column == "skill_rank_id":
                        continue
                    if any(token in column.casefold() for token in timing_tokens):
                        selected.append(column)
                    elif column in {"coefficient_number", "effect_kind", "source", "evidence", "description"}:
                        selected.append(column)
                selected = list(dict.fromkeys(selected))
                try:
                    rows = connection.execute(
                        f"SELECT {', '.join(selected)} FROM {table} WHERE skill_rank_id = ?",
                        (rank.skill_rank_id,),
                    ).fetchall()
                except sqlite3.Error:
                    continue
                if not rows:
                    continue
                found_component_timing = True
                print(f"{table}:")
                for row in rows:
                    values = []
                    for key in row.keys():
                        value = row[key]
                        if value in (None, ""):
                            continue
                        values.append(f"{key}={_clean(value)}")
                    print("  " + " | ".join(values))

            if not found_component_timing:
                print("component timing rows: none")
            print()

    print("Interpretation: compare top-level skill/ability duration against preserved component timing evidence.")
    print("Do not promote tooltip numbers into the scheduler unless the evidence source and semantics are explicit.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
