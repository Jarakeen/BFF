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
from services.eso_collectible_database_service import EsoCollectibleDatabaseService


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
        if any(hint in path.name.casefold() for hint in hints):
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
    prefixes = (
        "Recipe:", "Blueprint:", "Praxis:", "Diagram:",
        "Pattern:", "Design:", "Formula:", "Sketch:",
    )
    sample = records[: min(len(records), 5000)]
    return any(
        str(row.get("name") or "").startswith(prefixes)
        for row in sample
        if isinstance(row, dict)
    )


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

    for root in (project_root / name for name in _SCAN_ROOT_NAMES):
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


def _as_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_bool(value) -> int:
    return 1 if str(value or "").strip().casefold() in {"1", "yes", "true"} else 0


def _restore_furnishings_from_collectible_source(database: Path) -> tuple[int, int]:
    """Backfill Furniture collectibles from preserved entity/entity_source rows.

    This uses UPDATE/INSERT rather than INSERT OR REPLACE so existing
    collectible_progress rows are not deleted by SQLite replacement semantics.
    """
    service = EsoCollectibleDatabaseService(database)
    service.close()

    restored = 0
    source_rows = 0
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        tables = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        if not {"entity", "entity_source", "collectible"}.issubset(tables):
            return 0, 0

        rows = connection.execute(
            """
            SELECT e.id AS entity_id, e.name AS entity_name, es.raw_json
            FROM entity e
            JOIN entity_source es ON es.entity_id = e.id
            WHERE e.entity_type = 'collectible'
              AND es.raw_json IS NOT NULL
            ORDER BY es.id
            """
        ).fetchall()

        seen: set[str] = set()
        for row in rows:
            entity_id = str(row["entity_id"])
            if entity_id in seen:
                continue
            seen.add(entity_id)
            try:
                raw = json.loads(row["raw_json"])
            except (TypeError, json.JSONDecodeError):
                continue

            fields = raw.get("fields") or {}
            category_type = str(fields.get("categoryType") or "")
            category_name = str(fields.get("categoryName") or "")
            subcategory_name = str(fields.get("subCategoryName") or "")
            canonical_type, status = EsoCollectibleDatabaseService._classify(
                category_type,
                category_name,
                subcategory_name,
            )
            if canonical_type != "furnishing":
                continue

            collectible_id = _as_int(raw.get("collectible_id") or fields.get("id"))
            if collectible_id is None:
                continue
            source_rows += 1

            existing = connection.execute(
                "SELECT id FROM collectible WHERE id = ? OR entity_id = ? LIMIT 1",
                (collectible_id, entity_id),
            ).fetchone()

            values = {
                "entity_id": entity_id,
                "name": fields.get("name") or row["entity_name"] or f"Collectible {collectible_id}",
                "description": fields.get("description") or "",
                "hint": fields.get("hint") or "",
                "icon": fields.get("icon") or "",
                "source_category_type": category_type,
                "source_category_name": category_name,
                "source_subcategory_name": subcategory_name,
                "category_index": _as_int(fields.get("categoryIndex")),
                "subcategory_index": _as_int(fields.get("subCategoryIndex")),
                "collectible_index": _as_int(fields.get("collectibleIndex")),
                "canonical_type_key": "furnishing",
                "sidebar_category_key": "Furnishings",
                "normalization_status": status,
                "audit_reason": None,
                "is_unlocked": _as_bool(fields.get("isUnlocked")),
                "is_active": _as_bool(fields.get("isActive")),
                "is_slottable": _as_bool(fields.get("isSlottable")),
                "is_usable": _as_bool(fields.get("isUsable")),
                "is_renameable": _as_bool(fields.get("isRenameable")),
                "is_placeholder": _as_bool(fields.get("isPlaceholder")),
                "is_hidden": _as_bool(fields.get("isHidden")),
                "has_appearance": _as_bool(fields.get("hasAppearance")),
                "source_raw_json": row["raw_json"],
            }

            if existing is not None:
                assignments = ", ".join(f"{name} = ?" for name in values)
                connection.execute(
                    f"UPDATE collectible SET {assignments} WHERE id = ?",
                    (*values.values(), int(existing["id"])),
                )
            else:
                columns = ["id", *values.keys()]
                placeholders = ", ".join("?" for _ in columns)
                connection.execute(
                    f"INSERT INTO collectible ({', '.join(columns)}) VALUES ({placeholders})",
                    (collectible_id, *values.values()),
                )
            restored += 1

        connection.commit()

    return source_rows, restored


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
            "Restore FoundryDock Furnishings, Recipes/Furnishing Plans, and "
            "Lorebooks from preserved canonical/raw sources without replacing eso.db."
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
    print("Restoring Furniture collectibles from entity_source...")
    furnishing_source_rows, furnishings_restored = _restore_furnishings_from_collectible_source(database)
    print(f"  furnishing source rows: {furnishing_source_rows:,}")
    print(f"  furnishings upserted:   {furnishings_restored:,}")

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
        furnishings = _count(connection, "collectible", "sidebar_category_key = ?", ("Furnishings",))
        provisioning = _count(connection, "learnable_recipe", "learnable_kind = ?", ("provisioning_recipe",))
        plans = _count(connection, "learnable_recipe", "learnable_kind = ?", ("furnishing_plan",))
        mappings = _count(connection, "furnishing_plan_result")
        lorebooks = _count(connection, "lorebook")
        collectible_progress = _count(connection, "collectible_progress")
        recipe_progress = _count(connection, "learnable_recipe_progress")
        lore_progress = _count(connection, "lorebook_progress")

    print()
    print("========================================")
    print(" COLLECTION REFERENCE RECOVERY COMPLETE")
    print("========================================")
    print(f"Furnishings:             {furnishings:,}")
    print(f"Provisioning recipes:    {provisioning:,}")
    print(f"Furnishing plans:        {plans:,}")
    print(f"Furnishing mappings:     {mappings:,}")
    print(f"Lorebooks:               {lorebooks:,}")
    print(f"Collectible progress:    {collectible_progress:,}")
    print(f"Recipe progress rows:    {recipe_progress:,}")
    print(f"Lorebook progress rows:  {lore_progress:,}")

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
