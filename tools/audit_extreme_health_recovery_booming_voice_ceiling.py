from __future__ import annotations

"""Inspect canonical evidence needed to bound Booming Voice Health Recovery.

Booming Voice inherits The Storm Voice's ``Ultimate spent`` event. This audit keeps
stored Ultimate separate from the base cost of the Ultimate ability actually cast,
prints the canonical passive evidence, and enumerates the canonical base-cost
frontier of Ultimates that a pure Dragonknight can legally slot.

The cost authority is ``ability.base_cost`` via the same canonical model used by
``AbilityCostRepository``; ``skill_rank.cost`` is not used as a substitute.
"""

import argparse
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.resource_costs import ResourceType, decode_resource_mechanic
from services.class_mastery_repository import ClassMasteryRepository
from services.eso_character_progression_contract import ULTIMATE_RULES
from services.skill_bar_eligibility import is_eligible
from services.skill_choice_service import load_skill_choices


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    return parser


def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})").fetchall()}


def _select_existing(columns: set[str], names: tuple[str, ...], *, prefix: str = "") -> list[str]:
    result: list[str] = []
    for name in names:
        if name in columns:
            source = f"{prefix}.{name}" if prefix else name
            result.append(f"{source} AS {prefix + '_' if prefix else ''}{name}")
    return result


def main() -> int:
    args = _parser().parse_args()
    database = Path(args.database)

    mastery = tuple(
        row
        for row in ClassMasteryRepository(database).all()
        if row.name.casefold() == "booming voice"
    )

    print("EXTREME HEALTH RECOVERY BOOMING VOICE CEILING EVIDENCE")
    print(f"database={database}")
    print("mode=canonical_ability_base_cost_frontier_not_stored_ultimate_assumption")
    print()
    print("ULTIMATE CONTRACT")
    print(f"maximum_resource={ULTIMATE_RULES.maximum_resource}")
    print(f"one_ultimate_per_bar={ULTIMATE_RULES.one_ultimate_per_bar}")
    print(f"normal_cast_consumes_accumulated_resource={ULTIMATE_RULES.normal_cast_consumes_accumulated_resource}")
    print("stored_resource_is_not_assumed_spend_value=True")
    print()

    print("CLASS MASTERY ROW")
    if not mastery:
        print("  <missing Booming Voice Class Mastery row>")
    for row in mastery:
        print(
            f"  class={row.class_name!r} skill_id={row.skill_id} base_ability_id={row.base_ability_id} "
            f"name={row.name!r}"
        )
        print(f"  description={row.description!r}")
    print()

    if not database.is_file():
        print("database_missing=True")
        return 2

    with sqlite3.connect(database) as db:
        db.row_factory = sqlite3.Row
        skill_cols = _columns(db, "skill")
        rank_cols = _columns(db, "skill_rank")
        ability_cols = _columns(db, "ability")

        print("MATCHING SKILL ROWS")
        skill_select = _select_existing(
            skill_cols,
            (
                "id", "base_ability_id", "name", "class_type", "skill_line", "skill_type",
                "description", "is_passive", "is_player", "is_crafted",
            ),
            prefix="s",
        )
        if skill_select:
            text_parts = [
                "LOWER(COALESCE(s.name, ''))",
                "LOWER(COALESCE(s.description, ''))" if "description" in skill_cols else "''",
            ]
            rows = db.execute(
                f"SELECT {', '.join(skill_select)} FROM skill s "
                f"WHERE {' OR '.join(f'{part} LIKE ?' for part in text_parts for _ in (0, 1))} "
                "ORDER BY LOWER(COALESCE(s.name, '')), s.id",
                tuple(value for _part in text_parts for value in ("%storm voice%", "%booming voice%")),
            ).fetchall()
            if not rows:
                print("  <none>")
            for row in rows:
                print("  " + repr(dict(row)))
        else:
            print("  <skill schema unavailable>")
        print()

        print("MATCHING SKILL RANK / ABILITY ROWS")
        if {"skill_id", "ability_id"}.issubset(rank_cols) and "id" in skill_cols:
            select = []
            select.extend(_select_existing(skill_cols, ("id", "name", "class_type", "skill_line"), prefix="s"))
            select.extend(_select_existing(rank_cols, ("ability_id", "rank", "morph", "cost", "raw_name", "raw_description"), prefix="sr"))
            select.extend(_select_existing(ability_cols, ("name", "base_cost", "base_mechanic", "description"), prefix="a"))
            ability_join = "LEFT JOIN ability a ON a.ability_id = sr.ability_id" if "ability_id" in ability_cols else ""
            predicates = ["LOWER(COALESCE(s.name, '')) LIKE ?"]
            params: list[str] = ["%storm voice%"]
            if "raw_name" in rank_cols:
                predicates.append("LOWER(COALESCE(sr.raw_name, '')) LIKE ?")
                params.append("%storm voice%")
            if "raw_description" in rank_cols:
                predicates.append("LOWER(COALESCE(sr.raw_description, '')) LIKE ?")
                params.append("%storm voice%")
            if "name" in ability_cols:
                predicates.append("LOWER(COALESCE(a.name, '')) LIKE ?")
                params.append("%storm voice%")
            if "description" in ability_cols:
                predicates.append("LOWER(COALESCE(a.description, '')) LIKE ?")
                params.append("%storm voice%")
            rows = db.execute(
                f"SELECT {', '.join(select)} FROM skill_rank sr "
                "JOIN skill s ON s.id = sr.skill_id "
                f"{ability_join} "
                f"WHERE {' OR '.join(predicates)} "
                "ORDER BY s.id, COALESCE(sr.rank, 0), COALESCE(sr.morph, 0), sr.ability_id",
                tuple(params),
            ).fetchall()
            if not rows:
                print("  <none>")
            for row in rows:
                print("  " + repr(dict(row)))
        else:
            print("  <rank schema unavailable>")
        print()

        print("PURE DRAGONKNIGHT ULTIMATE BASE-COST FRONTIER")
        choices = tuple(
            row
            for row in load_skill_choices(database)
            if is_eligible(row, character_class="dragonknight", slot_index=5)
        )
        ability_ids = tuple(
            sorted({int(row.get("ability_id") or 0) for row in choices if int(row.get("ability_id") or 0) > 0})
        )
        cost_rows: list[dict[str, object]] = []
        if ability_ids and {"ability_id", "base_cost", "base_mechanic"}.issubset(ability_cols):
            placeholders = ",".join("?" for _ in ability_ids)
            rows = db.execute(
                f"SELECT ability_id, name, skill_line, base_cost, base_mechanic "
                f"FROM ability WHERE ability_id IN ({placeholders})",
                ability_ids,
            ).fetchall()
            choice_by_id = {int(row.get("ability_id") or 0): row for row in choices}
            for row in rows:
                ability_id = int(row["ability_id"] or 0)
                base_cost = row["base_cost"]
                base_mechanic = row["base_mechanic"]
                if base_cost is None or float(base_cost) <= 0 or base_mechanic is None:
                    continue
                try:
                    resources = decode_resource_mechanic(int(base_mechanic))
                except ValueError:
                    continue
                if ResourceType.ULTIMATE not in resources:
                    continue
                choice = choice_by_id.get(ability_id, {})
                cost_rows.append(
                    {
                        "ability_id": ability_id,
                        "name": str(choice.get("name") or row["name"] or ""),
                        "class_type": str(choice.get("class_type") or ""),
                        "skill_line": str(choice.get("skill_line") or row["skill_line"] or ""),
                        "rank": int(choice.get("rank") or 0),
                        "morph": int(choice.get("morph") or 0),
                        "base_cost": float(base_cost),
                        "base_mechanic": int(base_mechanic),
                    }
                )
        cost_rows.sort(key=lambda row: (-float(row["base_cost"]), str(row["name"]).casefold(), int(row["ability_id"])))
        if not cost_rows:
            print("  <no canonical cost-bearing ultimate candidates>")
        for row in cost_rows:
            print("  " + repr(row))

    print()
    max_cost = max((float(row["base_cost"]) for row in cost_rows), default=None)
    print(f"ultimate_choices_eligible={len(choices)}")
    print(f"ultimate_candidates_with_canonical_cost={len(cost_rows)}")
    print(f"maximum_legal_base_ultimate_cost={max_cost if max_cost is not None else '<unresolved>'}")
    if max_cost is not None:
        print(f"booming_voice_flat_ceiling_if_cost_semantics={max_cost * 5.0:.3f}")
        print("cost_authority=ability.base_cost")
        print("NEXT_STEP=wire the proven canonical Ultimate-cost ceiling into Booming Voice route scoring and compare against the 1341 subclass incumbent")
    else:
        print("NEXT_STEP=resolve missing ability.base_cost Ultimate evidence before assigning Booming Voice a numeric ceiling")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
