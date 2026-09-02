from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PLAN_PREFIXES = {
    "Blueprint",
    "Praxis",
    "Diagram",
    "Pattern",
    "Design",
    "Formula",
    "Sketch",
}

_FURNISHING_LINE_RE = re.compile(
    r'^\s*(\d+),\s*"(.*?)",\s*(\d+),\s*'
    r'(\|H\d+:item:[^|]+\|h\|h),\s*"(.*?)",\s*'
    r'(\|H\d+:item:[^|]+\|h\|h)\s*$'
)
_ITEM_ID_RE = re.compile(r"\|H\d+:item:(\d+):")


def _item_id_from_link(value: str | None) -> int | None:
    match = _ITEM_ID_RE.search(str(value or ""))
    return int(match.group(1)) if match else None


def _int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True)
class LearnedRecipeImportSummary:
    source_records: int
    provisioning_recipes: int
    furnishing_plans: int
    furnishing_mappings: int
    furnishing_rows_without_plan: int
    unresolved: tuple[str, ...]


class UespLearnedRecipeImporter:
    """Import provisioning recipes and furnishing plans from UESP exports.

    The recipe/plan item is the canonical learned object. Furnishing-result rows
    are a separate crosswalk from a furnishing plan item to the furnishing item
    it creates. Learned ownership is deliberately not imported here; that is a
    per-profile concern handled by the collection-progress layer.
    """

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    @staticmethod
    def load_recipe_export(path: str | Path) -> list[dict[str, Any]]:
        source = Path(path)
        payload = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"Expected an object in {source}")
        records = payload.get("minedItemSummary")
        if not isinstance(records, list):
            raise ValueError(f"Expected a minedItemSummary list in {source}")
        if any(not isinstance(record, dict) for record in records):
            raise ValueError(f"Non-object records found in {source}")
        declared = payload.get("numRecords")
        if declared not in (None, "") and int(declared) != len(records):
            raise ValueError(
                f"numRecords={declared} does not match minedItemSummary={len(records)} in {source}"
            )
        return list(records)

    @staticmethod
    def load_furnishing_export(path: str | Path) -> tuple[list[dict[str, Any]], int]:
        source = Path(path)
        rows: list[dict[str, Any]] = []
        without_plan = 0
        for line_number, line in enumerate(source.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
            if line_number == 1:
                continue
            match = _FURNISHING_LINE_RE.match(line)
            if match is None:
                # UESP's export uses ?, ? for furnishings without a learnable
                # recipe/plan. Those are intentionally excluded from this
                # learned-plan catalog.
                if re.search(r",\s*\?\s*,\s*\?\s*$", line):
                    without_plan += 1
                    continue
                continue
            (
                source_row,
                furnishing_name,
                furnishing_quality,
                furnishing_link,
                recipe_name,
                recipe_link,
            ) = match.groups()
            furnishing_item_id = _item_id_from_link(furnishing_link)
            plan_item_id = _item_id_from_link(recipe_link)
            if furnishing_item_id is None or plan_item_id is None:
                continue
            rows.append(
                {
                    "source_row": int(source_row),
                    "furnishing_item_id": furnishing_item_id,
                    "furnishing_name": furnishing_name,
                    "furnishing_quality": int(furnishing_quality),
                    "furnishing_item_link": furnishing_link,
                    "plan_item_id": plan_item_id,
                    "plan_name": recipe_name,
                    "plan_item_link": recipe_link,
                }
            )
        return rows, without_plan

    @staticmethod
    def _create_schema(connection: sqlite3.Connection) -> None:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS learnable_recipe (
                item_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                learnable_kind TEXT NOT NULL CHECK (learnable_kind IN ('provisioning_recipe', 'furnishing_plan')),
                plan_type TEXT NOT NULL,
                quality INTEGER,
                icon TEXT,
                craft_type INTEGER,
                special_type INTEGER,
                recipe_rank INTEGER,
                recipe_quality INTEGER,
                recipe_list_index INTEGER,
                recipe_index INTEGER,
                result_item_id INTEGER,
                result_item_link TEXT,
                ability_description TEXT,
                source_raw_json TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_learnable_recipe_kind
                ON learnable_recipe(learnable_kind, name);
            CREATE INDEX IF NOT EXISTS idx_learnable_recipe_result
                ON learnable_recipe(result_item_id);

            CREATE TABLE IF NOT EXISTS furnishing_plan_result (
                plan_item_id INTEGER NOT NULL,
                furnishing_item_id INTEGER NOT NULL,
                furnishing_name TEXT NOT NULL,
                furnishing_quality INTEGER,
                furnishing_item_link TEXT,
                source_row INTEGER,
                PRIMARY KEY (plan_item_id, furnishing_item_id),
                FOREIGN KEY (plan_item_id) REFERENCES learnable_recipe(item_id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_furnishing_plan_result_name
                ON furnishing_plan_result(furnishing_name);

            CREATE TABLE IF NOT EXISTS learnable_recipe_progress (
                profile_name TEXT NOT NULL,
                item_id INTEGER NOT NULL,
                learned INTEGER NOT NULL DEFAULT 0 CHECK (learned IN (0, 1)),
                learned_on TEXT,
                notes TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (profile_name, item_id),
                FOREIGN KEY (item_id) REFERENCES learnable_recipe(item_id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_learnable_recipe_progress_profile
                ON learnable_recipe_progress(profile_name, learned);
            """
        )

    def run(
        self,
        *,
        recipe_path: str | Path,
        furnishing_path: str | Path | None = None,
    ) -> LearnedRecipeImportSummary:
        records = self.load_recipe_export(recipe_path)
        furnishing_rows: list[dict[str, Any]] = []
        furnishing_rows_without_plan = 0
        if furnishing_path is not None:
            furnishing_rows, furnishing_rows_without_plan = self.load_furnishing_export(furnishing_path)

        unresolved: list[str] = []
        provisioning_count = 0
        furnishing_plan_count = 0

        with sqlite3.connect(self.database_path) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            self._create_schema(connection)

            seen_item_ids: set[int] = set()
            for record in sorted(records, key=lambda row: int(row.get("itemId") or 0)):
                item_id = _int(record.get("itemId"))
                name = str(record.get("name") or "").strip()
                if item_id is None or not name:
                    unresolved.append("Recipe export row lacks itemId or name")
                    continue
                if item_id in seen_item_ids:
                    unresolved.append(f"Duplicate recipe itemId {item_id}: {name}")
                    continue
                seen_item_ids.add(item_id)

                prefix = name.split(":", 1)[0].strip() if ":" in name else ""
                if prefix == "Recipe":
                    learnable_kind = "provisioning_recipe"
                    provisioning_count += 1
                elif prefix in PLAN_PREFIXES:
                    learnable_kind = "furnishing_plan"
                    furnishing_plan_count += 1
                else:
                    unresolved.append(f"Unrecognized learnable prefix for {item_id}: {name}")
                    continue

                result_item_link = str(record.get("resultItemLink") or "").strip()
                connection.execute(
                    """
                    INSERT INTO learnable_recipe (
                        item_id, name, learnable_kind, plan_type, quality, icon,
                        craft_type, special_type, recipe_rank, recipe_quality,
                        recipe_list_index, recipe_index, result_item_id,
                        result_item_link, ability_description, source_raw_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(item_id) DO UPDATE SET
                        name = excluded.name,
                        learnable_kind = excluded.learnable_kind,
                        plan_type = excluded.plan_type,
                        quality = excluded.quality,
                        icon = excluded.icon,
                        craft_type = excluded.craft_type,
                        special_type = excluded.special_type,
                        recipe_rank = excluded.recipe_rank,
                        recipe_quality = excluded.recipe_quality,
                        recipe_list_index = excluded.recipe_list_index,
                        recipe_index = excluded.recipe_index,
                        result_item_id = excluded.result_item_id,
                        result_item_link = excluded.result_item_link,
                        ability_description = excluded.ability_description,
                        source_raw_json = excluded.source_raw_json
                    """,
                    (
                        item_id,
                        name,
                        learnable_kind,
                        prefix,
                        _int(record.get("quality")),
                        str(record.get("icon") or ""),
                        _int(record.get("craftType")),
                        _int(record.get("specialType")),
                        _int(record.get("recipeRank")),
                        _int(record.get("recipeQuality")),
                        _int(record.get("recipeListIndex")),
                        _int(record.get("recipeIndex")),
                        _item_id_from_link(result_item_link),
                        result_item_link,
                        str(record.get("abilityDesc") or ""),
                        json.dumps(record, ensure_ascii=False),
                    ),
                )

            mapping_count = 0
            for row in furnishing_rows:
                plan = connection.execute(
                    "SELECT learnable_kind, name FROM learnable_recipe WHERE item_id = ?",
                    (row["plan_item_id"],),
                ).fetchone()
                if plan is None:
                    unresolved.append(
                        f"Furnishing {row['furnishing_item_id']} references unknown plan {row['plan_item_id']}"
                    )
                    continue
                if plan["learnable_kind"] != "furnishing_plan":
                    unresolved.append(
                        f"Furnishing {row['furnishing_item_id']} maps to non-furnishing recipe {row['plan_item_id']}"
                    )
                    continue
                if str(plan["name"]).casefold() != str(row["plan_name"]).casefold():
                    unresolved.append(
                        f"Plan-name mismatch for {row['plan_item_id']}: {plan['name']!r} vs {row['plan_name']!r}"
                    )
                    continue
                connection.execute(
                    """
                    INSERT INTO furnishing_plan_result (
                        plan_item_id, furnishing_item_id, furnishing_name,
                        furnishing_quality, furnishing_item_link, source_row
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(plan_item_id, furnishing_item_id) DO UPDATE SET
                        furnishing_name = excluded.furnishing_name,
                        furnishing_quality = excluded.furnishing_quality,
                        furnishing_item_link = excluded.furnishing_item_link,
                        source_row = excluded.source_row
                    """,
                    (
                        row["plan_item_id"],
                        row["furnishing_item_id"],
                        row["furnishing_name"],
                        row["furnishing_quality"],
                        row["furnishing_item_link"],
                        row["source_row"],
                    ),
                )
                mapping_count += 1

            connection.commit()

        return LearnedRecipeImportSummary(
            source_records=len(records),
            provisioning_recipes=provisioning_count,
            furnishing_plans=furnishing_plan_count,
            furnishing_mappings=mapping_count,
            furnishing_rows_without_plan=furnishing_rows_without_plan,
            unresolved=tuple(unresolved),
        )
