from __future__ import annotations

import sqlite3
from pathlib import Path

from .resource_cost_modifiers import ActionCostModifier, CostModifierOperation
from .resource_costs import ResourceType


_EFFECT_RESOURCES: dict[str, tuple[ResourceType, ...]] = {
    "magicka_cost_reduction": (ResourceType.MAGICKA,),
    "stamina_cost_reduction": (ResourceType.STAMINA,),
    "resource_cost_reduction": (
        ResourceType.HEALTH,
        ResourceType.MAGICKA,
        ResourceType.STAMINA,
    ),
}


class JewelryCostModifierRepository:
    """Load action-cost modifiers directly from existing jewelry glyph effects.

    Cost modifiers are resource events, not persistent character-sheet stats, so
    they deliberately bypass EffectMapper/StatId. The jewelry glyph importer is
    still the single source of stored glyph data.
    """

    def __init__(self, database_path: str | Path):
        self.database_path = str(database_path)

    def get_by_name(
        self,
        glyph_name: str,
        *,
        use_max_value: bool = True,
        multiplier: float = 1.0,
        source_prefix: str = "",
    ) -> tuple[ActionCostModifier, ...]:
        if multiplier < 0:
            raise ValueError("Jewelry cost modifier multiplier cannot be negative")

        with sqlite3.connect(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT
                    g.name,
                    e.effect_type,
                    e.value_min,
                    e.value_max,
                    e.unit
                FROM jewelry_glyph g
                JOIN jewelry_glyph_effect e
                    ON e.glyph_item_id = g.item_id
                WHERE LOWER(TRIM(g.name)) = LOWER(TRIM(?))
                ORDER BY COALESCE(e.value_max, e.value_min) DESC, e.id
                """,
                (glyph_name,),
            ).fetchall()

        strongest: list[tuple] = []
        seen_effect_types: set[str] = set()
        for row in rows:
            effect_type = str(row[1] or "").strip().casefold()
            if effect_type in seen_effect_types:
                continue
            seen_effect_types.add(effect_type)
            strongest.append(row)

        modifiers: list[ActionCostModifier] = []
        for stored_name, effect_type, value_min, value_max, unit in strongest:
            normalized_type = str(effect_type or "").strip().casefold()
            resources = _EFFECT_RESOURCES.get(normalized_type)
            if resources is None:
                continue

            value = value_max if use_max_value else value_min
            if value is None:
                value = value_min if use_max_value else value_max
            if value is None:
                raise ValueError(
                    f"Jewelry cost modifier has no usable value: {stored_name!r}"
                )

            normalized_unit = str(unit or "").strip().casefold()
            if normalized_unit == "flat":
                operation = CostModifierOperation.FLAT_REDUCTION
                modifier_value = float(value) * float(multiplier)
            elif normalized_unit == "percent":
                operation = CostModifierOperation.PERCENT_REDUCTION
                modifier_value = (float(value) / 100.0) * float(multiplier)
            else:
                raise ValueError(
                    f"Unsupported jewelry cost modifier unit: {unit!r}"
                )

            source = str(stored_name or glyph_name).strip()
            if source_prefix:
                source = f"{source_prefix}: {source}"

            modifiers.append(
                ActionCostModifier(
                    source=source,
                    operation=operation,
                    value=modifier_value,
                    resources=resources,
                )
            )

        return tuple(modifiers)
