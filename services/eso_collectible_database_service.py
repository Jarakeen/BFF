# ==================================================
# Black Feather Foundry
#
# File:
# services/eso_collectible_database_service.py
#
# Purpose:
# Read-only runtime access to normalized ESO collectibles,
# with a one-time bootstrap from canonical entity data when
# the normalized collectible catalog is missing.
#
# ==================================================

from __future__ import annotations

import json
import sqlite3
from pathlib import Path


SIDEBAR_CATEGORIES = [
    ("Mounts", 1),
    ("Pets", 2),
    ("Allies / Assistants", 3),
    ("Houses", 4),
    ("Costumes", 5),
    ("Skins", 6),
    ("Polymorphs", 7),
    ("Personalities", 8),
    ("Hairstyles & Adornments", 9),
    ("Mementos", 10),
    ("Emotes", 11),
    ("Customized Actions", 12),
]

TYPE_TO_SIDEBAR = {
    "mount": "Mounts",
    "pet": "Pets",
    "assistant": "Allies / Assistants",
    "companion": "Allies / Assistants",
    "house": "Houses",
    "costume": "Costumes",
    "skin": "Skins",
    "polymorph": "Polymorphs",
    "personality": "Personalities",
    "hair": "Hairstyles & Adornments",
    "hat": "Hairstyles & Adornments",
    "facial_accessory": "Hairstyles & Adornments",
    "facial_hair_horns": "Hairstyles & Adornments",
    "piercing_jewelry": "Hairstyles & Adornments",
    "body_marking": "Hairstyles & Adornments",
    "head_marking": "Hairstyles & Adornments",
    "memento": "Mementos",
    "emote": "Emotes",
    "customized_action": "Customized Actions",
}

DIRECT_TYPES = {
    "Mount": "mount",
    "Vanity Pet": "pet",
    "Assistant": "assistant",
    "House": "house",
    "Costume": "costume",
    "Skin": "skin",
    "Polymorph": "polymorph",
    "Personality": "personality",
    "Hair": "hair",
    "Hat": "hat",
    "Facial Accessory": "facial_accessory",
    "Facial Hair Horns": "facial_hair_horns",
    "Piercing Jewelry": "piercing_jewelry",
    "Body Marking": "body_marking",
    "Head Marking": "head_marking",
    "Emote": "emote",
    "Furniture": "furnishing",
}


class EsoCollectibleDatabaseService:
    """Database access for the dedicated Collections workspace."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = Path(database_path)
        self._connection: sqlite3.Connection | None = None
        self.available = False
        self.bootstrap_message = ""
        self.ensure_ready()

    @property
    def connection(self) -> sqlite3.Connection:
        if self._connection is None:
            self._connection = sqlite3.connect(self.database_path)
            self._connection.row_factory = sqlite3.Row
        return self._connection

    def _table_exists(self, name: str) -> bool:
        return self.connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (name,),
        ).fetchone() is not None

    def ensure_ready(self) -> None:
        """
        Use the normalized catalog if it already exists. Otherwise,
        build it once from canonical collectible entities. Missing raw
        source data is non-fatal so the rest of FoundryDock can launch.
        """
        try:
            self._create_schema()

            count = self.connection.execute(
                "SELECT COUNT(*) FROM collectible"
            ).fetchone()[0]

            if count == 0:
                if not self._table_exists("entity") or not self._table_exists("entity_source"):
                    self.bootstrap_message = "Collectible reference data has not been installed."
                    self.available = False
                    return

                raw_count = self.connection.execute(
                    "SELECT COUNT(*) FROM entity WHERE entity_type='collectible'"
                ).fetchone()[0]

                if raw_count == 0:
                    self.bootstrap_message = "Collectible reference data has not been installed."
                    self.available = False
                    return

                self._bootstrap_from_entity_source()
                count = self.connection.execute(
                    "SELECT COUNT(*) FROM collectible"
                ).fetchone()[0]
                self.bootstrap_message = f"Collectible catalog prepared ({count:,} records)."
            else:
                self.bootstrap_message = f"Collectible catalog ready ({count:,} records)."

            self.available = count > 0

        except sqlite3.Error as exc:
            self.available = False
            self.bootstrap_message = f"Collectible database unavailable: {exc}"

    def _create_schema(self) -> None:
        db = self.connection

        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS schema_migration (
                migration_key TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS collectible_sidebar_category (
                key TEXT PRIMARY KEY,
                display_name TEXT NOT NULL UNIQUE,
                sort_order INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS collectible_type (
                key TEXT PRIMARY KEY,
                display_name TEXT NOT NULL UNIQUE,
                sidebar_key TEXT
            );

            CREATE TABLE IF NOT EXISTS collectible (
                id INTEGER PRIMARY KEY,
                entity_id TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                description TEXT,
                hint TEXT,
                icon TEXT,
                source_category_type TEXT,
                source_category_name TEXT,
                source_subcategory_name TEXT,
                category_index INTEGER,
                subcategory_index INTEGER,
                collectible_index INTEGER,
                canonical_type_key TEXT,
                sidebar_category_key TEXT,
                normalization_status TEXT NOT NULL DEFAULT 'unmapped',
                mapping_id INTEGER,
                audit_reason TEXT,
                is_unlocked INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 0,
                is_slottable INTEGER DEFAULT 0,
                is_usable INTEGER DEFAULT 0,
                is_renameable INTEGER DEFAULT 0,
                is_placeholder INTEGER DEFAULT 0,
                is_hidden INTEGER DEFAULT 0,
                has_appearance INTEGER DEFAULT 0,
                source_raw_json TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_collectible_name
                ON collectible(name);
            CREATE INDEX IF NOT EXISTS idx_collectible_sidebar
                ON collectible(sidebar_category_key);
            CREATE INDEX IF NOT EXISTS idx_collectible_type
                ON collectible(canonical_type_key);
            CREATE INDEX IF NOT EXISTS idx_collectible_source_category
                ON collectible(source_category_name, source_subcategory_name);

            CREATE VIEW IF NOT EXISTS collectible_search AS
            SELECT
                c.*,
                t.display_name AS canonical_type_name,
                s.display_name AS sidebar_category_name
            FROM collectible c
            LEFT JOIN collectible_type t ON t.key = c.canonical_type_key
            LEFT JOIN collectible_sidebar_category s ON s.key = c.sidebar_category_key;

            CREATE VIEW IF NOT EXISTS collectible_audit AS
            SELECT *
            FROM collectible
            WHERE audit_reason IS NOT NULL;
            """
        )

        for name, order in SIDEBAR_CATEGORIES:
            db.execute(
                "INSERT OR IGNORE INTO collectible_sidebar_category(key, display_name, sort_order) VALUES (?, ?, ?)",
                (name, name, order),
            )

        type_names = {
            "mount": "Mount", "pet": "Pet", "assistant": "Assistant",
            "companion": "Companion", "house": "House", "costume": "Costume",
            "skin": "Skin", "polymorph": "Polymorph", "personality": "Personality",
            "hair": "Hair", "hat": "Hat", "facial_accessory": "Facial Accessory",
            "facial_hair_horns": "Facial Hair / Horns", "piercing_jewelry": "Piercing / Jewelry",
            "body_marking": "Body Marking", "head_marking": "Head Marking",
            "memento": "Memento", "emote": "Emote", "customized_action": "Customized Action",
            "furnishing": "Furnishing", "combination_fragment": "Combination Fragment",
            "fragment": "Fragment", "armor_style": "Armor Style", "weapon_style": "Weapon Style",
            "story": "Story", "patron": "Patron", "tool": "Tool",
            "account_upgrade": "Account Upgrade", "skill_style": "Skill Style",
        }

        for key, display in type_names.items():
            db.execute(
                "INSERT OR IGNORE INTO collectible_type(key, display_name, sidebar_key) VALUES (?, ?, ?)",
                (key, display, TYPE_TO_SIDEBAR.get(key)),
            )

        db.commit()

    @staticmethod
    def _bool(value) -> int:
        return 1 if str(value or "").strip().lower() in {"yes", "true", "1"} else 0

    @staticmethod
    def _int(value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _classify(category_type: str, category_name: str, subcategory_name: str):
        if category_type == "Invalid":
            return None, "invalid"

        if category_type in DIRECT_TYPES:
            return DIRECT_TYPES[category_type], "exact"

        contextual = {
            ("Unknown (27)", "Allies", "Companions"): "companion",
            ("Trophy", "Mementos", None): "memento",
            ("Unknown (29)", "Customized Actions", None): "customized_action",
            ("Combination Fragment", "Furnishings", None): "combination_fragment",
            ("Unknown (26)", "Fragments", None): "fragment",
            ("Outfit Style", "Armor Styles", None): "armor_style",
            ("Outfit Style", "Weapon Styles", None): "weapon_style",
            ("DLC", "Stories", None): "story",
            ("Unknown (28)", "Patrons", None): "patron",
            ("Trophy", "Tools", None): "tool",
            ("Account Upgrade", "Upgrade", None): "account_upgrade",
            ("Unknown (30)", "Appearance", "Skill Styles"): "skill_style",
        }

        exact = contextual.get((category_type, category_name, subcategory_name))
        if exact:
            return exact, "contextual"

        broad = contextual.get((category_type, category_name, None))
        if broad:
            return broad, "contextual"

        return None, "unmapped"

    def _bootstrap_from_entity_source(self) -> None:
        db = self.connection

        rows = db.execute(
            """
            SELECT e.id AS entity_id, e.name AS entity_name, es.raw_json
            FROM entity e
            JOIN entity_source es ON es.entity_id = e.id
            WHERE e.entity_type = 'collectible'
              AND es.raw_json IS NOT NULL
            ORDER BY es.id
            """
        ).fetchall()

        seen = set()
        insert_rows = []

        for row in rows:
            if row["entity_id"] in seen:
                continue
            seen.add(row["entity_id"])

            try:
                raw = json.loads(row["raw_json"])
            except (TypeError, json.JSONDecodeError):
                continue

            fields = raw.get("fields") or {}
            collectible_id = self._int(raw.get("collectible_id") or fields.get("id"))
            if collectible_id is None:
                continue

            category_type = fields.get("categoryType") or ""
            category_name = fields.get("categoryName") or ""
            subcategory_name = fields.get("subCategoryName") or ""
            canonical_type, status = self._classify(category_type, category_name, subcategory_name)
            sidebar = TYPE_TO_SIDEBAR.get(canonical_type)

            if status == "invalid":
                audit_reason = "invalid_source_type"
            elif canonical_type and not sidebar:
                audit_reason = "outside_sidebar"
            elif status == "unmapped":
                audit_reason = "unmapped"
            else:
                audit_reason = None

            insert_rows.append((
                collectible_id,
                row["entity_id"],
                fields.get("name") or row["entity_name"] or f"Collectible {collectible_id}",
                fields.get("description") or "",
                fields.get("hint") or "",
                fields.get("icon") or "",
                category_type,
                category_name,
                subcategory_name,
                self._int(fields.get("categoryIndex")),
                self._int(fields.get("subCategoryIndex")),
                self._int(fields.get("collectibleIndex")),
                canonical_type,
                sidebar,
                status,
                audit_reason,
                self._bool(fields.get("isUnlocked")),
                self._bool(fields.get("isActive")),
                self._bool(fields.get("isSlottable")),
                self._bool(fields.get("isUsable")),
                self._bool(fields.get("isRenameable")),
                self._bool(fields.get("isPlaceholder")),
                self._bool(fields.get("isHidden")),
                self._bool(fields.get("hasAppearance")),
                row["raw_json"],
            ))

        db.executemany(
            """
            INSERT OR REPLACE INTO collectible (
                id, entity_id, name, description, hint, icon,
                source_category_type, source_category_name, source_subcategory_name,
                category_index, subcategory_index, collectible_index,
                canonical_type_key, sidebar_category_key, normalization_status,
                audit_reason, is_unlocked, is_active, is_slottable, is_usable,
                is_renameable, is_placeholder, is_hidden, has_appearance,
                source_raw_json
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            insert_rows,
        )

        db.execute(
            "INSERT OR REPLACE INTO schema_migration(migration_key) VALUES ('collectibles_normalization_v1')"
        )
        db.commit()

    def category_count(self, category: str) -> int:
        if not self.available:
            return 0
        return self.connection.execute(
            "SELECT COUNT(*) FROM collectible WHERE sidebar_category_key = ?",
            (category,),
        ).fetchone()[0]

    def collectibles(self, category: str, query: str = "") -> list[dict]:
        if not self.available:
            return []

        query = query.strip()
        params = [category]
        where = "sidebar_category_key = ?"

        if query:
            pattern = f"%{query}%"
            where += " AND (name LIKE ? OR description LIKE ? OR hint LIKE ? OR source_subcategory_name LIKE ?)"
            params.extend([pattern, pattern, pattern, pattern])

        rows = self.connection.execute(
            f"""
            SELECT id, name, description, hint, icon,
                   canonical_type_key, source_subcategory_name,
                   is_unlocked, is_usable, is_renameable
            FROM collectible
            WHERE {where}
            ORDER BY name COLLATE NOCASE, id
            """,
            params,
        ).fetchall()

        return [dict(row) for row in rows]

    def collectible(self, collectible_id: int) -> dict | None:
        if not self.available:
            return None
        row = self.connection.execute(
            "SELECT * FROM collectible_search WHERE id = ?",
            (collectible_id,),
        ).fetchone()
        return dict(row) if row else None

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None
