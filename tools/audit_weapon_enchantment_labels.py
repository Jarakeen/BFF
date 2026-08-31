from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE


_EFFECT_HINTS: dict[str, tuple[str, str | None]] = {
    "weapon damage": ("weapon_spell_damage", None),
    "spell damage": ("weapon_spell_damage", None),
    "crushing": ("physical_spell_resistance_reduction", None),
    "frost": ("damage", "frost"),
    "flame": ("damage", "flame"),
    "shock": ("damage", "shock"),
    "poison": ("damage", "poison"),
    "disease": ("damage", "disease"),
}


def _normalize(value: object) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def _columns(db: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in db.execute(f"PRAGMA table_info({table})").fetchall()}


def _print_row(row: sqlite3.Row) -> None:
    print(
        "  - "
        f"item_id={row['item_id']} | "
        f"name={row['name'] or ''!r} | "
        f"enchant_name={row['enchant_name'] or ''!r} | "
        f"level_range={row['level_range'] or ''!r} | "
        f"quality_range={row['quality_range'] or ''!r} | "
        f"glyph_min_level={row['glyph_min_level'] or ''!r} | "
        f"craft_skill_rank={row['craft_skill_rank']!r} | "
        f"effect_type={row['effect_type'] or ''!r} | "
        f"damage_type={row['damage_type'] or ''!r} | "
        f"target={row['target'] or ''!r} | "
        f"value={row['value_max']!r} | "
        f"duration={row['duration_value']!r} {row['duration_unit'] or ''}"
    )


def audit(database: Path, labels: list[str]) -> int:
    if not database.exists():
        print(f"Database not found: {database}")
        return 1

    with sqlite3.connect(database) as db:
        db.row_factory = sqlite3.Row
        enchant_columns = _columns(db, "weapon_enchantment")
        effect_columns = _columns(db, "weapon_enchantment_effect")
        if not {"item_id", "name"}.issubset(enchant_columns):
            print("weapon_enchantment table is unavailable or incomplete.")
            return 2
        if not {"enchantment_item_id", "effect_type"}.issubset(effect_columns):
            print("weapon_enchantment_effect table is unavailable or incomplete.")
            return 3

        select_parts = [
            "w.item_id AS item_id",
            "w.name AS name",
            "w.enchant_name AS enchant_name" if "enchant_name" in enchant_columns else "'' AS enchant_name",
            "w.level_range AS level_range" if "level_range" in enchant_columns else "'' AS level_range",
            "w.quality_range AS quality_range" if "quality_range" in enchant_columns else "'' AS quality_range",
            "w.glyph_min_level AS glyph_min_level" if "glyph_min_level" in enchant_columns else "'' AS glyph_min_level",
            "w.craft_skill_rank AS craft_skill_rank" if "craft_skill_rank" in enchant_columns else "NULL AS craft_skill_rank",
            "e.effect_type AS effect_type",
            "e.damage_type AS damage_type" if "damage_type" in effect_columns else "'' AS damage_type",
            "e.target AS target" if "target" in effect_columns else "'' AS target",
            "e.value_max AS value_max" if "value_max" in effect_columns else "NULL AS value_max",
            "e.duration_value AS duration_value" if "duration_value" in effect_columns else "NULL AS duration_value",
            "e.duration_unit AS duration_unit" if "duration_unit" in effect_columns else "'' AS duration_unit",
        ]
        select_sql = ", ".join(select_parts)

        print("========================================")
        print(" WEAPON ENCHANTMENT LABEL AUDIT")
        print("========================================")
        print(f"Database: {database}")

        for label in labels:
            normalized = _normalize(label)
            print()
            print(f"Saved label: {label}")

            exact_predicates = ["LOWER(TRIM(w.name)) = LOWER(TRIM(?))"]
            exact_params: list[str] = [label]
            if "enchant_name" in enchant_columns:
                exact_predicates.append("LOWER(TRIM(w.enchant_name)) = LOWER(TRIM(?))")
                exact_params.append(label)

            exact = db.execute(
                f"""
                SELECT {select_sql}
                FROM weapon_enchantment w
                LEFT JOIN weapon_enchantment_effect e
                  ON e.enchantment_item_id = w.item_id
                WHERE {' OR '.join(exact_predicates)}
                ORDER BY w.item_id, e.id
                """,
                tuple(exact_params),
            ).fetchall()
            print(f"Exact name/enchant_name matches: {len(exact)}")
            for row in exact:
                _print_row(row)

            hint = _EFFECT_HINTS.get(normalized)
            if hint is None:
                print("Semantic effect hint: none registered for this audit label")
                continue

            effect_type, damage_type = hint
            predicates = ["e.effect_type = ?"]
            params: list[object] = [effect_type]
            if damage_type is not None:
                predicates.append("LOWER(COALESCE(e.damage_type, '')) = ?")
                params.append(damage_type)

            candidates = db.execute(
                f"""
                SELECT {select_sql}
                FROM weapon_enchantment w
                JOIN weapon_enchantment_effect e
                  ON e.enchantment_item_id = w.item_id
                WHERE {' AND '.join(predicates)}
                ORDER BY COALESCE(w.craft_skill_rank, -1) DESC, w.item_id DESC, e.id
                """,
                tuple(params),
            ).fetchall()

            print(
                "Semantic candidates: "
                f"effect_type={effect_type!r}"
                + (f", damage_type={damage_type!r}" if damage_type else "")
                + f" -> {len(candidates)} row(s)"
            )
            for row in candidates:
                _print_row(row)

    print()
    print("Audit only: no database or saved-build data were changed.")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect how Builds UI enchant labels correspond to imported weapon-enchantment rows."
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("labels", nargs="*", default=["Weapon Damage", "Crushing"])
    return parser


if __name__ == "__main__":
    args = _parser().parse_args()
    raise SystemExit(audit(args.database, list(args.labels)))
