import sqlite3
from pathlib import Path

from .effects import EffectUnit
from .rule_effects import RuleEffect


class RuleRepository:
    """Loads rule-effect data from the ESO database."""

    def __init__(self, database_path: str | Path):
        self.database_path = str(database_path)

    def get_infused_effect(
        self,
        *,
        gear_type: str,
        quality: str,
    ) -> RuleEffect:

        with sqlite3.connect(self.database_path) as connection:
            row = connection.execute(
                """
                SELECT
                    trait_name,
                    effect_type,
                    value,
                    unit
                FROM jewelry_trait_effect
                WHERE trait_name = 'Infused'
                  AND effect_type = 'enchantment_effect'
                  AND item_type = ?
                  AND quality = ?
                """,
                (gear_type, quality),
            ).fetchone()

        if row is None:
            raise ValueError(
                f"No Infused enchantment effect found for "
                f"gear_type={gear_type!r}, quality={quality!r}"
            )

        trait_name, effect_type, value, unit = row

        return RuleEffect(
            rule_type=effect_type,
            value=float(value),
            source=trait_name,
            unit=EffectUnit(unit),
            target_system="enchantment",
            gear_type=gear_type,
            quality=quality,
        )

    def get_weapon_trait_rules(
        self,
        trait_name: str,
    ) -> list[RuleEffect]:

        with sqlite3.connect(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT
                    material_name,
                    effect_type,
                    value,
                    unit,
                    description
                FROM weapon_trait_effect
                WHERE material_name = ?
                ORDER BY id
                """,
                (trait_name,),
            ).fetchall()

        effects: list[RuleEffect] = []

        for (
            material_name,
            effect_type,
            value,
            unit,
            description,
        ) in rows:

            if value is None:
                raise ValueError(
                    f"Weapon trait rule has no value: "
                    f"{trait_name!r} / {effect_type!r}"
                )

            effects.append(
                RuleEffect(
                    rule_type=effect_type,
                    value=float(value),
                    source=material_name,
                    unit=EffectUnit(unit),
                    target_system="weapon_enchantment",
                )
            )

        return effects