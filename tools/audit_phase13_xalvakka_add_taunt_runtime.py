from __future__ import annotations

"""Audit canonical taunt events against Xalvakka Iron Atronach and Daedroth instances.

The canonical production database proves which skill-rank ability IDs own a TAUNT
utility component. The dedicated ESO Logs research database then proves whether those
exact ability IDs were observed from friendly sources against named add instances.

This audit is evidence-first: a matching taunt ability event proves observed taunt
application/cast evidence, but does not by itself prove continuous aggro ownership for
the entire add lifetime.
"""

import argparse
from dataclasses import dataclass
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.skill_component_utility_effect import SkillComponentUtilityEffectType
from minmax.skill_component_utility_effect_repository import SkillComponentUtilityEffectRepository

_DEFAULT_RESEARCH_DB = ROOT / "research" / "xalvakka_esologs_runtime.db"
_DEFAULT_GAME_DB = ROOT / "data" / "eso.db"
_TARGET_NAMES = ("Iron Atronach", "Daedroth")


@dataclass(frozen=True)
class CanonicalTauntAbility:
    ability_id: int
    skill_name: str


def canonical_taunt_abilities(game_db: Path) -> tuple[CanonicalTauntAbility, ...]:
    utility = SkillComponentUtilityEffectRepository(game_db)
    db = sqlite3.connect(game_db)
    db.row_factory = sqlite3.Row
    try:
        rows = db.execute(
            """
            SELECT DISTINCT sr.id AS skill_rank_id,
                            sr.ability_id,
                            s.name AS skill_name,
                            sc.coefficient_number
            FROM skill_rank sr
            JOIN skill s ON s.id = sr.skill_id
            JOIN skill_coefficient sc ON sc.skill_rank_id = sr.id
            WHERE sr.ability_id IS NOT NULL
            ORDER BY s.name, sr.ability_id, sc.coefficient_number
            """
        ).fetchall()
    finally:
        db.close()

    found: dict[int, str] = {}
    for row in rows:
        effects = utility.resolve(
            int(row["skill_rank_id"]),
            int(row["coefficient_number"]),
        )
        if any(effect.effect_type is SkillComponentUtilityEffectType.TAUNT for effect in effects):
            found.setdefault(int(row["ability_id"]), str(row["skill_name"]))
    return tuple(
        CanonicalTauntAbility(ability_id=ability_id, skill_name=found[ability_id])
        for ability_id in sorted(found)
    )


def audit(research_db: Path, game_db: Path) -> tuple[str, ...]:
    taunts = canonical_taunt_abilities(game_db)
    if not taunts:
        return ("UNRESOLVED: canonical game database exposes no TAUNT skill-rank ability IDs",)

    connection = sqlite3.connect(research_db)
    connection.row_factory = sqlite3.Row
    try:
        actor_rows = connection.execute(
            """
            SELECT report_code, actor_id, name
            FROM log_report_actor
            WHERE name IN (?, ?)
            ORDER BY report_code, name, actor_id
            """,
            _TARGET_NAMES,
        ).fetchall()
        if not actor_rows:
            return ("UNRESOLVED: no named Xalvakka add actors are available in report master data",)

        taunt_by_id = {row.ability_id: row.skill_name for row in taunts}
        ability_ids = tuple(sorted(taunt_by_id))
        placeholders = ",".join("?" for _ in ability_ids)
        lines = [
            "PHASE 13 XALVAKKA ADD TAUNT RUNTIME AUDIT",
            f"RESEARCH_DATABASE: {research_db}",
            f"GAME_DATABASE: {game_db}",
            "CANONICAL_TAUNTS: "
            + ", ".join(f"{row.skill_name}={row.ability_id}" for row in taunts),
        ]
        total = 0
        targeted_instances: set[tuple[str, int, int, int]] = set()

        by_report: dict[str, dict[str, set[int]]] = {}
        for row in actor_rows:
            by_report.setdefault(str(row["report_code"]), {}).setdefault(str(row["name"]), set()).add(int(row["actor_id"]))

        for report_code, actor_map in sorted(by_report.items()):
            for actor_name in _TARGET_NAMES:
                actor_ids = tuple(sorted(actor_map.get(actor_name, ())))
                if not actor_ids:
                    continue
                actor_placeholders = ",".join("?" for _ in actor_ids)
                rows = connection.execute(
                    f"""
                    SELECT e.fight_id,
                           e.timestamp,
                           e.event_type,
                           e.source_id,
                           e.target_id,
                           COALESCE(e.target_instance, 0) AS target_instance,
                           e.ability_game_id,
                           f.start_time
                    FROM log_event e
                    JOIN log_fight f
                      ON f.report_code = e.report_code AND f.fight_id = e.fight_id
                    WHERE e.report_code = ?
                      AND lower(trim(f.name)) = 'xalvakka'
                      AND e.source_is_friendly = 1
                      AND e.target_is_friendly = 0
                      AND e.target_id IN ({actor_placeholders})
                      AND e.ability_game_id IN ({placeholders})
                    ORDER BY e.fight_id, e.timestamp, e.event_index
                    """,
                    (report_code, *actor_ids, *ability_ids),
                ).fetchall()
                for row in rows:
                    relative = (float(row["timestamp"]) - float(row["start_time"] or 0.0)) / 1000.0
                    ability_id = int(row["ability_game_id"])
                    lines.append(
                        "TAUNT_EVENT: "
                        f"report={report_code} fight_id={int(row['fight_id'])} "
                        f"actor={actor_name} instance={int(row['target_instance'])} "
                        f"time={relative:.3f}s event={row['event_type']} "
                        f"source_id={row['source_id']} ability={taunt_by_id[ability_id]} "
                        f"ability_id={ability_id}"
                    )
                    total += 1
                    targeted_instances.add(
                        (
                            report_code,
                            int(row["fight_id"]),
                            int(row["target_id"]),
                            int(row["target_instance"]),
                        )
                    )

        lines.append(f"OBSERVED_TAUNT_EVENTS={total}")
        lines.append(f"TAUNTED_ADD_INSTANCES={len(targeted_instances)}")
        if total:
            lines.append(
                "INTERPRETATION=matching canonical TAUNT ability events prove observed add taunt actions; continuous ownership/uptime requires lifecycle evidence"
            )
        else:
            lines.append(
                "UNRESOLVED=no canonical TAUNT ability events were observed against named Xalvakka add instances"
            )
        return tuple(lines)
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=_DEFAULT_RESEARCH_DB)
    parser.add_argument("--game-db", type=Path, default=_DEFAULT_GAME_DB)
    args = parser.parse_args()
    for path in (args.db, args.game_db):
        if not path.exists():
            print(f"AUDIT ERROR: database does not exist: {path}")
            return 2
    try:
        for line in audit(args.db, args.game_db):
            print(line)
        return 0
    except (sqlite3.Error, ValueError) as exc:
        print(f"AUDIT ERROR: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
