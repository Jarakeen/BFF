import sqlite3
from pathlib import Path

from .combat_effects import CombatEffect
from .effects import EffectUnit


_SAVED_LABEL_EFFECT_ALIASES = {
    "weapon damage": "weapon_spell_damage",
    "crushing": "physical_spell_resistance_reduction",
}


class WeaponEnchantmentRepository:
    """Loads weapon enchantment identities and combat effects from ESO data."""

    def __init__(self, database_path: str | Path):
        self.database_path = str(database_path)

    def find_item_ids_by_label(self, label: str) -> tuple[int, ...]:
        """Return exact or semantically verified matches for one saved label.

        Legacy Builds stores short UI labels while imported ESO rows may expose
        longer item/enchantment names. Exact normalized name matches are tried
        first. Known UI labels may then map to a canonical effect type that the
        imported effect table can verify. Multiple matches remain visible to
        callers rather than being guessed away.
        """
        value = " ".join(str(label or "").strip().split())
        if not value:
            return ()

        normalized = value.casefold()
        with sqlite3.connect(self.database_path) as connection:
            columns = {
                str(row[1])
                for row in connection.execute(
                    "PRAGMA table_info(weapon_enchantment)"
                ).fetchall()
            }
            if not {"item_id", "name"}.issubset(columns):
                return ()

            predicates = ["LOWER(TRIM(name)) = LOWER(TRIM(?))"]
            parameters: list[str] = [value]
            if "enchant_name" in columns:
                predicates.append("LOWER(TRIM(enchant_name)) = LOWER(TRIM(?))")
                parameters.append(value)

            rows = connection.execute(
                f"""
                SELECT DISTINCT item_id
                FROM weapon_enchantment
                WHERE {' OR '.join(predicates)}
                ORDER BY item_id
                """,
                tuple(parameters),
            ).fetchall()
            exact = tuple(int(row[0]) for row in rows)
            if exact:
                return exact

            effect_type = _SAVED_LABEL_EFFECT_ALIASES.get(normalized)
            if effect_type is None:
                return ()

            effect_columns = {
                str(row[1])
                for row in connection.execute(
                    "PRAGMA table_info(weapon_enchantment_effect)"
                ).fetchall()
            }
            required = {"enchantment_item_id", "effect_type"}
            if not required.issubset(effect_columns):
                return ()

            rows = connection.execute(
                """
                SELECT DISTINCT enchantment_item_id
                FROM weapon_enchantment_effect
                WHERE effect_type = ?
                ORDER BY enchantment_item_id
                """,
                (effect_type,),
            ).fetchall()

        return tuple(int(row[0]) for row in rows)

    def get_effects(
        self,
        item_id: int,
        *,
        use_max_value: bool = True,
    ) -> list[CombatEffect]:

        with sqlite3.connect(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT
                    w.name,
                    e.effect_type,
                    e.damage_type,
                    e.target,
                    e.value_min,
                    e.value_max,
                    e.unit,
                    e.duration_value,
                    e.duration_unit,
                    e.scaling_type
                FROM weapon_enchantment w
                JOIN weapon_enchantment_effect e
                    ON e.enchantment_item_id = w.item_id
                WHERE w.item_id = ?
                ORDER BY e.id
                """,
                (item_id,),
            ).fetchall()

        effects: list[CombatEffect] = []

        for row in rows:
            (
                enchantment_name,
                effect_type,
                damage_type,
                target,
                value_min,
                value_max,
                unit,
                duration_value,
                duration_unit,
                scaling_type,
            ) = row

            value = value_max if use_max_value else value_min

            if value is None:
                raise ValueError(
                    f"Weapon enchantment effect has no usable value: "
                    f"{enchantment_name!r}"
                )

            effects.append(
                CombatEffect(
                    effect_type=effect_type,
                    value=float(value),
                    source=enchantment_name,
                    unit=EffectUnit(unit),
                    damage_type=damage_type,
                    target=target,
                    duration_value=duration_value,
                    duration_unit=duration_unit,
                    scaling_type=scaling_type,
                )
            )

        return effects