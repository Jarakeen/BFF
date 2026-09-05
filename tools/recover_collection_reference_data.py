from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.config import DEFAULT_DATABASE
from importers.learned_recipe_importer import UespLearnedRecipeImporter
from importers.lorebook_importer import UespLorebookImporter


_JSON_HINTS = ("recipe", "furnish", "book", "lore")
_TEXT_HINTS = ("furnish", "recipe", "plan")
_SCAN_ROOT_NAMES = ("research", "data")


def _candidate_files(root: Path, suffixes: set[str], hints: tuple[str, ...]) -> list[Path]:
    files: list[Path] = []
    if not root.exists():
        return files
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.casefold() not in suffixes:
            continue
        name = path.name.casefold()
        if any(hint in name for hint in hints):
            files.append(path)
    return sorted(files)


def _looks_like_recipe_export(path: Path) -> bool:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return False
    if not isinstance(payload, dict):
        return False
    records = payload.get("minedItemSummary")
    if not isinstance(records, list) or not records:
        return False
    prefixes = ("Recipe:", "Blueprint:", "Praxis:", "Diagram:", "Pattern:", "Design:", "Formula:", "Sketch:")
    sample = records[: min(len(records), 5000)]
    return any(str(row.get("name") or "").startswith(prefixes) for row in sample if isinstance(row, dict))


def _looks_like_lorebook_export(path: Path) -> bool:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return False
    if not isinstance(payload, dict):
        return False
    rows = payload.get("book")
    if not isinstance(rows, list) or not rows:
        return False
    return any(
        isinstance(row, dict)
        and "isLore" in row
        and ("title" in row or "body" in row)
        for row in rows[: min(len(rows), 5000)]
    )


def _looks_like_furnishing_export(path: Path) -> bool:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            sample = "\n".join(handle.readline() for _ in range(40))
    except OSError:
        return False
    text = sample.casefold()
    return "|h" in text and "item:" in text and ("recipe" in text or ", ?" in text)


def _discover(project_root: Path) -> dict[str, list[Path]]:
    recipe_candidates: list[Path] = []
    lorebook_candidates: list[Path] = []
    furnishing_candidates: list[Path] = []

    roots = [project_root / name for name in _SCAN_ROOT_NAMES]
    for root in roots:
        for path in _candidate_files(root, {".json"}, _JSON_HINTS):
            if _looks_like_recipe_export(path):
                recipe_candidates.append(path)
            if _looks_like_lorebook_export(path):
                lorebook_candidates.append(path)

        for path in _candidate_files(root, {".txt", ".csv", ".tsv"}, _TEXT_HINTS):
            if _looks_like_furnishing_export(path):
                furnishing_candidates.append(path)

    return {
        "recipes": sorted(set(recipe_candidates)),
        "lorebooks": sorted(set(lorebook_candidates)),
        "furnishings": sorted(set(furnishing_candidates)),
    }


def _choose(explicit: str | None, candidates: list[Path], label: str) -> Path | None:
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"{label} source not found: {path}")
        return path
    if len(candidates) == 1:
        return candidates[0]
    return None


def _count(connection: sqlite3.Connection, table: str, where: str = "", params: tuple = ()) -> int:
    sql = f"SELECT COUNT(*) FROM {table}"
    if where:
        sql += f" WHERE {where}"
    try:
        return int(connection.execute(sql, params).fetchone()[0])
    except sqlite3.Error:
        return 0


def _print_candidates(discovered: dict[str, list[Path]]) -> None:
    print("Discovered source candidates:")
    for label in ("recipes", "furnishings", "lorebooks"):
        values = discovered[label]
        print(f"  {label}: {len(values)}")
        for path in values:
            print(f"    - {path}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Restore FoundryDock Recipes, Furnishing Plans/results, and Lorebooks "
            "from existing local UESP source exports without replacing eso.db."
        )
    )
    parser.add_argument("--recipes", help="Explicit minedItemSummary recipe/furnishing-plan JSON")
    parser.add_argument("--furnishings", help="Explicit UESP viewFurnishings text/CSV export")
    parser.add_argument("--books", help="Explicit UESP books.json export")
    parser.add_argument("--database", default=str(DEFAULT_DATABASE), help=f"Target database (default: {DEFAULT_DATABASE})")
    parser.add_argument("--discover-only", action="store_true", help="Only locate likely source files; make no database changes")
    parser.add_argument("--no-backup", action="store_true", help="Skip the timestamped database backup")
    args = parser.parse_args()

    database = Path(args.database).expanduser().resolve()
    if not database.is_file():
        raise FileNotFoundError(f"Canonical database not found: {database}")

    discovered = _discover(PROJECT_ROOT)
    _print_candidates(discovered)

    recipe_path = _choose(args.recipes, discovered["recipes"], "Recipe")
    furnishing_path = _choose(args.furnishings, discovered["furnishings"], "Furnishing")
    books_path = _choose(args.books, discovered["lorebooks"], "Lorebook")

    if args.discover_only:
        return 0

    missing: list[str] = []
    if recipe_path is None:
        missing.append("recipe/furnishing-plan JSON")
    if books_path is None:
        missing.append("lorebook books.json")
    if missing:
        print()
        print("Recovery stopped before touching the database.")
        print("Could not uniquely resolve: " + ", ".join(missing))
        print("Pass the matching --recipes and/or --books path shown above.")
        return 2

    if not args.no_backup:
        stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
        backup = database.with_name(f"{database.name}.before-collection-reference-recovery.{stamp}")
        shutil.copy2(database, backup)
        print(f"Backup: {backup}")

    print()
    print("Restoring Recipes / Furnishing Plans...")
    recipe_summary = UespLearnedRecipeImporter(database).run(
        recipe_path=recipe_path,
        furnishing_path=furnishing_path,
    )
    print(f"  source records:       {recipe_summary.source_records:,}")
    print(f"  provisioning recipes: {recipe_summary.provisioning_recipes:,}")
    print(f"  furnishing plans:     {recipe_summary.furnishing_plans:,}")
    print(f"  furnishing mappings:  {recipe_summary.furnishing_mappings:,}")
    print(f"  unresolved:           {len(recipe_summary.unresolved):,}")

    print()
    print("Restoring Lorebooks...")
    lore_summary = UespLorebookImporter(database).run(books_path=books_path)
    print(f"  source records:      {lore_summary.source_records:,}")
    print(f"  lore source records: {lore_summary.lore_source_records:,}")
    print(f"  canonical lorebooks: {lore_summary.canonical_lorebooks:,}")
    print(f"  collapsed repeats:   {lore_summary.collapsed_occurrences:,}")
    print(f"  unresolved:          {len(lore_summary.unresolved):,}")

    with sqlite3.connect(database) as connection:
        provisioning = _count(connection, "learnable_recipe", "learnable_kind = ?", ("provisioning_recipe",))
        plans = _count(connection, "learnable_recipe", "learnable_kind = ?", ("furnishing_plan",))
        mappings = _count(connection, "furnishing_plan_result")
        lorebooks = _count(connection, "lorebook")
        recipe_progress = _count(connection, "learnable_recipe_progress")
        lore_progress = _count(connection, "lorebook_progress")

    print()
    print("========================================")
    print(" COLLECTION REFERENCE RECOVERY COMPLETE")
    print("========================================")
    print(f"Provisioning recipes:   {provisioning:,}")
    print(f"Furnishing plans:       {plans:,}")
    print(f"Furnishing mappings:    {mappings:,}")
    print(f"Lorebooks:              {lorebooks:,}")
    print(f"Recipe progress rows:   {recipe_progress:,}")
    print(f"Lorebook progress rows: {lore_progress:,}")

    unresolved = tuple(recipe_summary.unresolved) + tuple(lore_summary.unresolved)
    if unresolved:
        print()
        print(f"Recovery completed with {len(unresolved):,} unresolved source row(s).")
        for item in unresolved[:25]:
            print(f"  - {item}")
        if len(unresolved) > 25:
            print(f"  ... {len(unresolved) - 25:,} more")
        return 3

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
