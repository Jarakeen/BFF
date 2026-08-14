from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional


# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

DATABASE_FILE = (
    ROOT
    / "data"
    / "eso.db"
)


# ============================================================
# IMPORTER
# ============================================================

class AbilityCombatEffectImporter:

    def __init__(
        self,
        database_path: Path = DATABASE_FILE,
    ):
        self.database_path = Path(database_path)

    # ========================================================
    # RUN
    # ========================================================

    def run(self):

        print()
        print("=========================================")
        print(" Black Feather Foundry")
        print(" Ability → Combat Effect Importer")
        print("=========================================")
        print()

        print(
            f"Database: {self.database_path}"
        )

        print()

        db = sqlite3.connect(
            self.database_path
        )

        db.row_factory = sqlite3.Row

        try:

            self._verify_tables(db)

            self._create_table(db)

            self._clear_table(db)

            ability_lookup = (
                self._build_ability_lookup(db)
            )

            effect_lookup = (
                self._build_effect_lookup(db)
            )

            print(
                f"Abilities available: "
                f"{len(ability_lookup):,}"
            )

            print(
                f"Combat effects available: "
                f"{len(effect_lookup):,}"
            )

            print()

            mappings = (
                self._explicit_mappings()
            )

            print(
                f"Explicit mappings: "
                f"{len(mappings):,}"
            )

            print()

            inserted = 0
            unresolved_abilities = []
            unresolved_effects = []

            for mapping in mappings:

                effect_name = (
                    mapping["effect"]
                )

                effect_id = (
                    effect_lookup.get(
                        self._normalize(
                            effect_name
                        )
                    )
                )

                if effect_id is None:

                    unresolved_effects.append(
                        mapping
                    )

                    continue

                ability_name = (
                    mapping["ability"]
                )

                ability_ids = (
                    ability_lookup.get(
                        self._normalize(
                            ability_name
                        ),
                        [],
                    )
                )

                if not ability_ids:

                    unresolved_abilities.append(
                        mapping
                    )

                    continue

                for ability_id in ability_ids:

                    if self._insert_link(
                        db,
                        ability_id=ability_id,
                        effect_id=effect_id,
                        relationship=mapping[
                            "relationship"
                        ],
                        weapon_type=mapping.get(
                            "weapon_type"
                        ),
                        condition=mapping.get(
                            "condition"
                        ),
                        source=mapping.get(
                            "source",
                            "ESO Wiki",
                        ),
                        confidence=mapping.get(
                            "confidence",
                            "explicit",
                        ),
                    ):

                        inserted += 1

            db.commit()

            self._report(
                db,
                inserted,
                unresolved_abilities,
                unresolved_effects,
            )

        except Exception:

            db.rollback()
            raise

        finally:

            db.close()

    # ========================================================
    # VERIFY TABLES
    # ========================================================

    def _verify_tables(
        self,
        db: sqlite3.Connection,
    ):

        tables = {
            row["name"]
            for row in db.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                """
            )
        }

        required = {
            "ability",
            "combat_effect",
        }

        missing = (
            required - tables
        )

        if missing:

            raise RuntimeError(
                "Required tables are missing: "
                + ", ".join(
                    sorted(missing)
                )
            )

    # ========================================================
    # CREATE TABLE
    # ========================================================

    def _create_table(
        self,
        db: sqlite3.Connection,
    ):

        db.execute(
            """
            CREATE TABLE IF NOT EXISTS
            ability_combat_effect (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                ability_id INTEGER NOT NULL,

                combat_effect_id INTEGER NOT NULL,

                relationship TEXT NOT NULL,

                weapon_type TEXT,

                condition TEXT,

                source TEXT,

                confidence TEXT,

                raw_source TEXT,

                FOREIGN KEY (
                    ability_id
                )
                REFERENCES ability(id)
                ON DELETE CASCADE,

                FOREIGN KEY (
                    combat_effect_id
                )
                REFERENCES combat_effect(id)
                ON DELETE CASCADE,

                UNIQUE (
                    ability_id,
                    combat_effect_id,
                    relationship,
                    weapon_type,
                    condition
                )
            )
            """
        )

        db.commit()

    # ========================================================
    # CLEAR
    # ========================================================

    def _clear_table(
        self,
        db: sqlite3.Connection,
    ):

        db.execute(
            """
            DELETE FROM
            ability_combat_effect
            """
        )

        db.commit()

    # ========================================================
    # ABILITY LOOKUP
    # ========================================================

    def _build_ability_lookup(
        self,
        db: sqlite3.Connection,
    ):

        rows = db.execute(
            """
            SELECT
                id,
                name
            FROM ability
            WHERE name IS NOT NULL
            """
        ).fetchall()

        lookup = {}

        for row in rows:

            name = (
                self._normalize(
                    row["name"]
                )
            )

            if not name:
                continue

            lookup.setdefault(
                name,
                [],
            ).append(
                int(row["id"])
            )

        return lookup

    # ========================================================
    # EFFECT LOOKUP
    # ========================================================

    def _build_effect_lookup(
        self,
        db: sqlite3.Connection,
    ):

        rows = db.execute(
            """
            SELECT
                id,
                name
            FROM combat_effect
            """
        ).fetchall()

        lookup = {}

        for row in rows:

            name = (
                self._normalize(
                    row["name"]
                )
            )

            if not name:
                continue

            lookup[name] = int(
                row["id"]
            )

        return lookup

    # ========================================================
    # EXPLICIT MAPPINGS
    # ========================================================

    def _explicit_mappings(self):

        mappings = []

        # ====================================================
        # WALL OF ELEMENTS
        #
        # Weapon-specific behavior.
        #
        # These are deliberately separate records.
        # ====================================================

        mappings.extend(
            [

                {
                    "ability": "Wall of Elements",
                    "effect": "Burning",
                    "relationship": "Applies",
                    "weapon_type": "Flame Staff",
                    "condition": None,
                    "source": "ESO Wiki",
                    "confidence": "explicit",
                },

                {
                    "ability": "Wall of Elements",
                    "effect": "Chilled",
                    "relationship": "Applies",
                    "weapon_type": "Ice Staff",
                    "condition": None,
                    "source": "ESO Wiki",
                    "confidence": "explicit",
                },

                {
                    "ability": "Wall of Elements",
                    "effect": "Concussion",
                    "relationship": "Applies",
                    "weapon_type": "Lightning Staff",
                    "condition": None,
                    "source": "ESO Wiki",
                    "confidence": "explicit",
                },

                {
                    "ability": "Wall of Elements",
                    "effect": "Off Balance",
                    "relationship": "Applies",
                    "weapon_type": "Lightning Staff",
                    "condition": (
                        "Target must be Concussed"
                    ),
                    "source": "ESO Wiki",
                    "confidence": "explicit",
                },

            ]
        )

        # ====================================================
        # ELEMENTAL BLOCKADE
        # ====================================================

        mappings.extend(
            [

                {
                    "ability": "Elemental Blockade",
                    "effect": "Burning",
                    "relationship": "Applies",
                    "weapon_type": "Flame Staff",
                    "condition": None,
                    "source": "ESO Wiki",
                    "confidence": "explicit",
                },

                {
                    "ability": "Elemental Blockade",
                    "effect": "Chilled",
                    "relationship": "Applies",
                    "weapon_type": "Ice Staff",
                    "condition": None,
                    "source": "ESO Wiki",
                    "confidence": "explicit",
                },

                {
                    "ability": "Elemental Blockade",
                    "effect": "Concussion",
                    "relationship": "Applies",
                    "weapon_type": "Lightning Staff",
                    "condition": None,
                    "source": "ESO Wiki",
                    "confidence": "explicit",
                },

                {
                    "ability": "Elemental Blockade",
                    "effect": "Off Balance",
                    "relationship": "Applies",
                    "weapon_type": "Lightning Staff",
                    "condition": (
                        "Target must be Concussed"
                    ),
                    "source": "ESO Wiki",
                    "confidence": "explicit",
                },

            ]
        )

        # ====================================================
        # UNSTABLE WALL OF ELEMENTS
        # ====================================================

        mappings.extend(
            [

                {
                    "ability": "Unstable Wall of Elements",
                    "effect": "Burning",
                    "relationship": "Applies",
                    "weapon_type": "Flame Staff",
                    "condition": None,
                    "source": "ESO Wiki",
                    "confidence": "explicit",
                },

                {
                    "ability": "Unstable Wall of Elements",
                    "effect": "Chilled",
                    "relationship": "Applies",
                    "weapon_type": "Ice Staff",
                    "condition": None,
                    "source": "ESO Wiki",
                    "confidence": "explicit",
                },

                {
                    "ability": "Unstable Wall of Elements",
                    "effect": "Concussion",
                    "relationship": "Applies",
                    "weapon_type": "Lightning Staff",
                    "condition": None,
                    "source": "ESO Wiki",
                    "confidence": "explicit",
                },

                {
                    "ability": "Unstable Wall of Elements",
                    "effect": "Off Balance",
                    "relationship": "Applies",
                    "weapon_type": "Lightning Staff",
                    "condition": (
                        "Target must be Concussed"
                    ),
                    "source": "ESO Wiki",
                    "confidence": "explicit",
                },

            ]
        )

        # ====================================================
        # BLOCKADE OF STORMS
        #
        # Lightning-specific named ability.
        # ====================================================

        mappings.extend(
            [

                {
                    "ability": "Blockade of Storms",
                    "effect": "Concussion",
                    "relationship": "Applies",
                    "weapon_type": "Lightning Staff",
                    "condition": None,
                    "source": "ESO Wiki",
                    "confidence": "explicit",
                },

                {
                    "ability": "Blockade of Storms",
                    "effect": "Off Balance",
                    "relationship": "Applies",
                    "weapon_type": "Lightning Staff",
                    "condition": (
                        "Target must be Concussed"
                    ),
                    "source": "ESO Wiki",
                    "confidence": "explicit",
                },

            ]
        )

        # ====================================================
        # WALL OF STORMS
        # ====================================================

        mappings.extend(
            [

                {
                    "ability": "Wall of Storms",
                    "effect": "Concussion",
                    "relationship": "Applies",
                    "weapon_type": "Lightning Staff",
                    "condition": None,
                    "source": "ESO Wiki",
                    "confidence": "explicit",
                },

                {
                    "ability": "Wall of Storms",
                    "effect": "Off Balance",
                    "relationship": "Applies",
                    "weapon_type": "Lightning Staff",
                    "condition": (
                        "Target must be Concussed"
                    ),
                    "source": "ESO Wiki",
                    "confidence": "explicit",
                },

            ]
        )

        # ====================================================
        # CRUSHING SHOCK
        # ====================================================

        mappings.append(
            {
                "ability": "Crushing Shock",
                "effect": "Off Balance",
                "relationship": "Applies",
                "weapon_type": "Lightning Staff",
                "condition": (
                    "Target must be interrupted "
                    "while spellcasting"
                ),
                "source": "ESO Wiki",
                "confidence": "explicit",
            }
        )

        # ====================================================
        # TOPPLING CHARGE
        # ====================================================

        mappings.append(
            {
                "ability": "Toppling Charge",
                "effect": "Off Balance",
                "relationship": "Applies",
                "weapon_type": None,
                "condition": None,
                "source": "ESO Wiki",
                "confidence": "explicit",
            }
        )

        # ====================================================
        # SURPRISE ATTACK
        # ====================================================

        mappings.append(
            {
                "ability": "Surprise Attack",
                "effect": "Off Balance",
                "relationship": "Applies",
                "weapon_type": "Dual Wield",
                "condition": (
                    "Must cast while flanking"
                ),
                "source": "ESO Wiki",
                "confidence": "explicit",
            }
        )

        # ====================================================
        # CONCEALED WEAPON
        # ====================================================

        mappings.append(
            {
                "ability": "Concealed Weapon",
                "effect": "Off Balance",
                "relationship": "Applies",
                "weapon_type": "Dual Wield",
                "condition": (
                    "Must cast while flanking"
                ),
                "source": "ESO Wiki",
                "confidence": "explicit",
            }
        )

        # ====================================================
        # VEILED STRIKE
        # ====================================================

        mappings.append(
            {
                "ability": "Veiled Strike",
                "effect": "Off Balance",
                "relationship": "Applies",
                "weapon_type": "Dual Wield",
                "condition": (
                    "Must cast while flanking"
                ),
                "source": "ESO Wiki",
                "confidence": "explicit",
            }
        )

        # ====================================================
        # VENOM ARROW
        # ====================================================

        mappings.append(
            {
                "ability": "Venom Arrow",
                "effect": "Off Balance",
                "relationship": "Applies",
                "weapon_type": "Bow",
                "condition": (
                    "Target must be interrupted "
                    "while spellcasting"
                ),
                "source": "ESO Wiki",
                "confidence": "explicit",
            }
        )

        # ====================================================
        # RUINOUS SCYTHE
        # ====================================================

        mappings.append(
            {
                "ability": "Ruinous Scythe",
                "effect": "Off Balance",
                "relationship": "Applies",
                "weapon_type": None,
                "condition": None,
                "source": "ESO Wiki",
                "confidence": "explicit",
            }
        )

        # ====================================================
        # DIZZYING SWING
        # ====================================================

        mappings.append(
            {
                "ability": "Dizzying Swing",
                "effect": "Off Balance",
                "relationship": "Applies",
                "weapon_type": "Two Handed",
                "condition": None,
                "source": "ESO Wiki",
                "confidence": "explicit",
            }
        )

        # ====================================================
        # POUNCE
        # ====================================================

        mappings.append(
            {
                "ability": "Pounce",
                "effect": "Off Balance",
                "relationship": "Applies",
                "weapon_type": None,
                "condition": None,
                "source": "ESO Wiki",
                "confidence": "explicit",
            }
        )

        # ====================================================
        # ROAR
        # ====================================================

        mappings.append(
            {
                "ability": "Roar",
                "effect": "Off Balance",
                "relationship": "Applies",
                "weapon_type": None,
                "condition": None,
                "source": "ESO Wiki",
                "confidence": "explicit",
            }
        )

        # ====================================================
        # DEEP BREATH
        # ====================================================

        mappings.append(
            {
                "ability": "Deep Breath",
                "effect": "Off Balance",
                "relationship": "Applies",
                "weapon_type": None,
                "condition": (
                    "Target must be interrupted "
                    "while spellcasting"
                ),
                "source": "ESO Wiki",
                "confidence": "explicit",
            }
        )

        # ====================================================
        # SHATTERING ROCKS
        # ====================================================

        mappings.append(
            {
                "ability": "Shattering Rocks",
                "effect": "Off Balance",
                "relationship": "Applies",
                "weapon_type": None,
                "condition": (
                    "Occurs after 20 seconds; "
                    "50% chance"
                ),
                "source": "ESO Wiki",
                "confidence": "explicit",
            }
        )

        # ====================================================
        # DIVE
        # ====================================================

        mappings.append(
            {
                "ability": "Dive",
                "effect": "Off Balance",
                "relationship": "Applies",
                "weapon_type": None,
                "condition": (
                    "Target must be at least 7 meters away"
                ),
                "source": "ESO Wiki",
                "confidence": "explicit",
            }
        )

        # ====================================================
        # LAVA WHIP
        # ====================================================

        mappings.append(
            {
                "ability": "Lava Whip",
                "effect": "Off Balance",
                "relationship": "Interacts",
                "weapon_type": None,
                "condition": (
                    "Target must already be "
                    "Off Balance"
                ),
                "source": "ESO Wiki",
                "confidence": "explicit",
            }
        )

        return mappings

    # ========================================================
    # INSERT
    # ========================================================

    def _insert_link(
        self,
        db: sqlite3.Connection,
        ability_id: int,
        effect_id: int,
        relationship: str,
        weapon_type: Optional[str],
        condition: Optional[str],
        source: str,
        confidence: str,
        raw_source: Optional[str] = None,
    ) -> bool:

        cursor = db.execute(
            """
            INSERT OR IGNORE INTO
            ability_combat_effect (

                ability_id,
                combat_effect_id,

                relationship,

                weapon_type,
                condition,

                source,
                confidence,

                raw_source
            )
            VALUES (
                ?, ?,
                ?,
                ?, ?,
                ?, ?,
                ?
            )
            """,
            (
                ability_id,
                effect_id,

                relationship,

                weapon_type,
                condition,

                source,
                confidence,

                raw_source,
            ),
        )

        return (
            cursor.rowcount > 0
        )

    # ========================================================
    # NORMALIZE
    # ========================================================

    @staticmethod
    def _normalize(
        value,
    ) -> str:

        if value is None:
            return ""

        return " ".join(
            str(value)
            .strip()
            .casefold()
            .split()
        )

    # ========================================================
    # REPORT
    # ========================================================

    def _report(
        self,
        db: sqlite3.Connection,
        inserted: int,
        unresolved_abilities: list[dict],
        unresolved_effects: list[dict],
    ):

        total = db.execute(
            """
            SELECT COUNT(*)
            FROM ability_combat_effect
            """
        ).fetchone()[0]

        unique_abilities = db.execute(
            """
            SELECT COUNT(
                DISTINCT ability_id
            )
            FROM ability_combat_effect
            """
        ).fetchone()[0]

        unique_effects = db.execute(
            """
            SELECT COUNT(
                DISTINCT combat_effect_id
            )
            FROM ability_combat_effect
            """
        ).fetchone()[0]

        print()
        print(
            "## Ability → Combat Effect "
            "Import Complete"
        )
        print()

        print(
            f"Links created:       {inserted:,}"
        )

        print(
            f"Total links:         {total:,}"
        )

        print(
            f"Unique abilities:    "
            f"{unique_abilities:,}"
        )

        print(
            f"Combat effects used: "
            f"{unique_effects:,}"
        )

        print()

        # ----------------------------------------------------
        # BY EFFECT
        # ----------------------------------------------------

        print(
            "=== LINKS BY EFFECT ==="
        )

        rows = db.execute(
            """
            SELECT
                ce.name,
                COUNT(*) AS count
            FROM ability_combat_effect ace
            JOIN combat_effect ce
                ON ce.id =
                   ace.combat_effect_id
            GROUP BY ce.id
            ORDER BY ce.name
            """
        ).fetchall()

        for row in rows:

            print(
                f"{row['name']:20} "
                f"{row['count']}"
            )

        print()

        # ----------------------------------------------------
        # BY RELATIONSHIP
        # ----------------------------------------------------

        print(
            "=== LINKS BY RELATIONSHIP ==="
        )

        rows = db.execute(
            """
            SELECT
                relationship,
                COUNT(*)
            FROM ability_combat_effect
            GROUP BY relationship
            ORDER BY relationship
            """
        ).fetchall()

        for row in rows:

            print(
                f"{row[0]:12} "
                f"{row[1]}"
            )

        print()

        # ----------------------------------------------------
        # BY WEAPON
        # ----------------------------------------------------

        print(
            "=== LINKS BY WEAPON ==="
        )

        rows = db.execute(
            """
            SELECT
                COALESCE(
                    weapon_type,
                    '(none)'
                ),
                COUNT(*)
            FROM ability_combat_effect
            GROUP BY weapon_type
            ORDER BY weapon_type
            """
        ).fetchall()

        for row in rows:

            print(
                f"{row[0]:20} "
                f"{row[1]}"
            )

        print()

        # ----------------------------------------------------
        # OFF BALANCE
        # ----------------------------------------------------

        print(
            "=== OFF BALANCE SOURCES ==="
        )

        rows = db.execute(
            """
            SELECT
                a.name,
                ace.relationship,
                ace.weapon_type,
                ace.condition,
                ace.confidence
            FROM ability_combat_effect ace
            JOIN ability a
                ON a.id =
                   ace.ability_id
            JOIN combat_effect ce
                ON ce.id =
                   ace.combat_effect_id
            WHERE ce.name =
                  'Off Balance'
            ORDER BY
                a.name,
                ace.weapon_type
            """
        ).fetchall()

        for row in rows:

            print(
                f"{row['name']} | "
                f"{row['relationship']} | "
                f"weapon="
                f"{row['weapon_type']} | "
                f"condition="
                f"{row['condition']} | "
                f"{row['confidence']}"
            )

        print()

        # ----------------------------------------------------
        # UNRESOLVED ABILITIES
        # ----------------------------------------------------

        print(
            "=== UNRESOLVED ABILITIES ==="
        )

        if not unresolved_abilities:

            print(
                "None"
            )

        else:

            seen = set()

            for mapping in (
                unresolved_abilities
            ):

                key = (
                    mapping["ability"],
                    mapping["effect"],
                )

                if key in seen:
                    continue

                seen.add(key)

                print(
                    f"{mapping['ability']} "
                    f"→ "
                    f"{mapping['effect']}"
                )

        print()

        # ----------------------------------------------------
        # UNRESOLVED EFFECTS
        # ----------------------------------------------------

        print(
            "=== UNRESOLVED EFFECTS ==="
        )

        if not unresolved_effects:

            print(
                "None"
            )

        else:

            seen = set()

            for mapping in (
                unresolved_effects
            ):

                effect = (
                    mapping["effect"]
                )

                if effect in seen:
                    continue

                seen.add(effect)

                print(
                    effect
                )

        print()


# ============================================================
# MAIN
# ============================================================

def main():

    importer = (
        AbilityCombatEffectImporter()
    )

    importer.run()


if __name__ == "__main__":
    main()