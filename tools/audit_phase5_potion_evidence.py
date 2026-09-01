from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE, get_data_dir
from models.build_model import PlayerBuild

DEFAULT_BUILDS = get_data_dir() / "builds.json"

# The Builds UI currently stores a human preset label, not an ESO item id.
# Audit the component effects that could define that preset. This is evidence
# only; it does not assert that every UI label maps to these effects.
_PRESET_EFFECT_CANDIDATES: dict[str, tuple[str, ...]] = {
    "spell power": (
        "Increase Spell Power",
        "Spell Critical",
        "Restore Magicka",
    ),
}


def _load_saved_build(path: Path, requested: str) -> PlayerBuild:
    payload = json.loads(path.read_text(encoding="utf-8"))
    members = payload.get("Members") if isinstance(payload, dict) else None
    if not isinstance(members, list):
        raise ValueError(f"Unsupported saved-build format in {path}; expected Members")

    key = requested.strip().casefold()
    matches = [
        PlayerBuild.from_dict(entry)
        for entry in members
        if isinstance(entry, dict)
        and str(entry.get("BuildName", "")).strip().casefold() == key
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Expected exactly one saved build named {requested!r}; found {len(matches)}"
        )
    return matches[0]


def _tables(connection: sqlite3.Connection) -> set[str]:
    return {
        str(row[0])
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }


def _effect_rows(connection: sqlite3.Connection, effect_name: str):
    return connection.execute(
        """
        SELECT e.id, e.name, e.category, ev.id, ev.type, ev.description,
               ev.raw_json
        FROM effect e
        JOIN effect_variant ev ON ev.effect_id = e.id
        WHERE LOWER(TRIM(e.name)) = LOWER(TRIM(?))
          AND LOWER(TRIM(COALESCE(ev.type, ''))) = 'potion'
        ORDER BY ev.id
        """,
        (effect_name,),
    ).fetchall()


def _formula_key(formula: dict) -> tuple[tuple[str, ...], tuple[str, ...]]:
    ingredients = tuple(
        sorted(str(value).strip().casefold() for value in formula.get("ingredients", []) if str(value).strip())
    )
    effects = tuple(
        sorted(str(value).strip().casefold() for value in formula.get("effects", []) if str(value).strip())
    )
    return ingredients, effects


def audit_potion_evidence(
    *,
    database_path: Path,
    builds_path: Path,
    build_name: str,
) -> int:
    if not database_path.exists():
        print(f"Database not found: {database_path}")
        return 1
    if not builds_path.exists():
        print(f"Saved builds not found: {builds_path}")
        return 2

    try:
        saved = _load_saved_build(builds_path, build_name)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(exc)
        return 3

    label = str(saved.Potion or "").strip()
    candidates = _PRESET_EFFECT_CANDIDATES.get(label.casefold(), ())

    print("========================================")
    print(" PHASE 5 POTION EVIDENCE AUDIT")
    print("========================================")
    print(f"Database:     {database_path}")
    print(f"Saved builds: {builds_path}")
    print(f"Character:    {saved.Name or '(unnamed)'}")
    print(f"Build:        {saved.BuildName or '(unnamed)'}")
    print(f"Saved potion: {label or '(none)'}")
    print()

    if not label:
        print("No potion is selected on this saved build.")
        return 0
    if not candidates:
        print("No audited preset candidate mapping exists for this saved label.")
        print("Audit only: no database or saved-build data were changed.")
        return 0

    with sqlite3.connect(database_path) as connection:
        required = {"effect", "effect_variant"}
        missing = required - _tables(connection)
        if missing:
            print("Missing required tables: " + ", ".join(sorted(missing)))
            return 4

        formula_sets: dict[str, set[tuple[tuple[str, ...], tuple[str, ...]]]] = {}
        raw_formulas: dict[str, list[dict]] = {}

        for effect_name in candidates:
            rows = _effect_rows(connection, effect_name)
            print("----------------------------------------")
            print(effect_name)
            print("----------------------------------------")
            print(f"Potion variants: {len(rows)}")
            formulas: list[dict] = []
            formula_keys: set[tuple[tuple[str, ...], tuple[str, ...]]] = set()

            if not rows:
                print("  (none found)")
                formula_sets[effect_name] = set()
                raw_formulas[effect_name] = []
                continue

            for effect_id, name, category, variant_id, variant_type, description, raw_json in rows:
                print(
                    f"  effect_id={effect_id} | variant_id={variant_id} | "
                    f"category={category!r} | type={variant_type!r}"
                )
                if description:
                    print(f"  description={description}")

                try:
                    payload = json.loads(raw_json) if raw_json else {}
                except json.JSONDecodeError:
                    payload = {}

                tiers = payload.get("tiers", []) if isinstance(payload, dict) else []
                source_formulas = payload.get("formulas", []) if isinstance(payload, dict) else []
                print(f"  tiers={len(tiers) if isinstance(tiers, list) else 0}")
                print(f"  formulas={len(source_formulas) if isinstance(source_formulas, list) else 0}")

                if isinstance(source_formulas, list):
                    for formula in source_formulas:
                        if not isinstance(formula, dict):
                            continue
                        key = _formula_key(formula)
                        if key not in formula_keys:
                            formula_keys.add(key)
                            formulas.append(formula)

            formula_sets[effect_name] = formula_keys
            raw_formulas[effect_name] = formulas
            for index, formula in enumerate(formulas[:12], start=1):
                ingredients = ", ".join(str(x) for x in formula.get("ingredients", [])) or "(none)"
                effects = ", ".join(str(x) for x in formula.get("effects", [])) or "(none)"
                print(f"  formula {index}: ingredients=[{ingredients}] | effects=[{effects}]")
            if len(formulas) > 12:
                print(f"  ... {len(formulas) - 12} more formula(s)")

    non_empty_sets = [values for values in formula_sets.values() if values]
    common = set.intersection(*non_empty_sets) if non_empty_sets and len(non_empty_sets) == len(candidates) else set()

    print()
    print("Cross-effect evidence:")
    if common:
        print(
            "  The imported source contains formula record(s) shared across all "
            "candidate effects for this saved preset."
        )
        for ingredients, effects in sorted(common)[:10]:
            print(
                "  - ingredients=[" + ", ".join(ingredients) + "] | effects=[" + ", ".join(effects) + "]"
            )
    else:
        print(
            "  No single normalized formula record is shared by all candidate "
            "effects. Do not infer a composite preset from this audit alone."
        )

    print()
    print("Audit only: no database or saved-build data were changed.")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit saved potion labels against imported UESP alchemy evidence."
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--builds", type=Path, default=DEFAULT_BUILDS)
    parser.add_argument("--build", default="DF Healer")
    return parser


if __name__ == "__main__":
    args = _parser().parse_args()
    raise SystemExit(
        audit_potion_evidence(
            database_path=args.database,
            builds_path=args.builds,
            build_name=args.build,
        )
    )
