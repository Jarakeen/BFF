import sqlite3
from pathlib import Path

from .combat_effects import CombatEffect
from .effects import EffectUnit


class WeaponEnchantmentRepository:
    """Loads weapon enchantment combat effects from the ESO database."""

    def __init__(self, database_path: str | Path):
        self.database_path = str(database_path)

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