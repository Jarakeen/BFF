from __future__ import annotations

"""Finite runtime-condition state for Extreme max-resource gear effects.

This service owns only condition legality/evidence. It does not perform stat math.
The reviewed max-resource denominator currently contains eight condition markers.
Some are exact finite runtime states and can be satisfied without changing the
materialized build; others depend on the selected build/consumable state and must
be proven from canonical evidence before they may be activated.

Ability-slot and transformation witnesses remain explicit blockers here until the
later bar/runtime services own their exact materialization. That prevents the
optimizer from treating "maximize" as permission to turn every condition on.
"""

from dataclasses import dataclass
from pathlib import Path
import sqlite3

from models.build_model import PlayerBuild


_SUPPORTED_OBJECTIVES = ("max_health", "max_magicka", "max_stamina")
_STACK_CONDITIONS = frozenset(
    {
        "escalating_fete_stacks:30",
        "prowlers_talisman_critical_stacks:10",
    }
)
_ABILITY_OR_TRANSFORM_CONDITIONS = frozenset(
    {
        "armor_ability_slotted",
        "pet_active",
        "transformed",
    }
)
_DESTRUCTION_STAFF_TYPES = frozenset(
    {
        "inferno staff",
        "lightning staff",
        "ice staff",
        "destruction staff",
    }
)


@dataclass(frozen=True)
class ExtremeResourceRuntimeConditionState:
    objective_key: str
    required_conditions: tuple[str, ...]
    active_conditions: tuple[str, ...]
    unresolved_conditions: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()

    @property
    def condition_context(self) -> frozenset[str]:
        return frozenset(self.active_conditions)

    @property
    def projection_complete(self) -> bool:
        return not self.unresolved_conditions and set(self.required_conditions).issubset(
            self.condition_context
        )

    @property
    def identity(self) -> tuple[object, ...]:
        return (
            self.objective_key,
            self.required_conditions,
            self.active_conditions,
            self.unresolved_conditions,
        )


class ExtremeResourceRuntimeConditionStateService:
    """Prove executable condition markers for one materialized Extreme candidate."""

    SUPPORTED_OBJECTIVES = _SUPPORTED_OBJECTIVES

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = str(database_path)
        self._provisioning_kind_cache: dict[str, str | None] = {}

    @staticmethod
    def _normalize_conditions(values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    str(value or "").strip()
                    for value in values
                    if str(value or "").strip()
                },
                key=str.casefold,
            )
        )

    def _provisioning_kind(self, name: str) -> str | None:
        selected = str(name or "").strip()
        if not selected:
            return None
        key = selected.casefold()
        if key in self._provisioning_kind_cache:
            return self._provisioning_kind_cache[key]

        kind: str | None = None
        with sqlite3.connect(self.database_path) as connection:
            table = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='entity'"
            ).fetchone()
            if table is not None:
                row = connection.execute(
                    """
                    SELECT entity_type
                    FROM entity
                    WHERE lower(name)=lower(?)
                      AND entity_type IN ('food', 'drink', 'provisioning')
                    ORDER BY CASE entity_type WHEN 'food' THEN 0 WHEN 'drink' THEN 1 ELSE 2 END
                    LIMIT 1
                    """,
                    (selected,),
                ).fetchone()
                if row is not None:
                    candidate = str(row[0] or "").strip().casefold()
                    if candidate in {"food", "drink"}:
                        kind = candidate

        self._provisioning_kind_cache[key] = kind
        return kind

    @staticmethod
    def _active_weapon_type(build: PlayerBuild, active_bar: str) -> str:
        main, _ = build.active_weapon_slots(active_bar)
        return str(main.WeaponType or "").strip().casefold()

    def build(
        self,
        objective_key: str,
        *,
        required_conditions: tuple[str, ...],
        build: PlayerBuild,
        active_bar: str = "front",
        food: str = "",
    ) -> ExtremeResourceRuntimeConditionState:
        key = str(objective_key or "").strip().casefold()
        if key not in _SUPPORTED_OBJECTIVES:
            raise KeyError(f"unreviewed Extreme runtime-condition objective: {objective_key!r}")

        required = self._normalize_conditions(required_conditions)
        active: set[str] = set()
        unresolved: list[str] = []
        evidence: list[str] = []

        weapon_type = self._active_weapon_type(build, active_bar)
        provisioning_kind = self._provisioning_kind(food)

        for condition in required:
            if condition in _STACK_CONDITIONS:
                active.add(condition)
                evidence.append(f"{condition}: reviewed finite maximum runtime state")
                continue

            if condition == "destruction_staff_equipped":
                if weapon_type in _DESTRUCTION_STAFF_TYPES:
                    active.add(condition)
                    evidence.append(
                        f"destruction_staff_equipped: active weapon type is {weapon_type}"
                    )
                else:
                    unresolved.append(
                        "destruction_staff_equipped requires an active-bar Destruction Staff witness"
                    )
                continue

            if condition == "food_buff_active":
                if provisioning_kind == "food":
                    active.add(condition)
                    evidence.append(f"food_buff_active: canonical provisioning type for {food}")
                elif food:
                    unresolved.append(
                        f"food_buff_active is not proven by selected provisioning item: {food}"
                    )
                else:
                    unresolved.append("food_buff_active requires a selected canonical food")
                continue

            if condition == "drink_buff_active":
                if provisioning_kind == "drink":
                    active.add(condition)
                    evidence.append(f"drink_buff_active: canonical provisioning type for {food}")
                elif food:
                    unresolved.append(
                        f"drink_buff_active is not proven by selected provisioning item: {food}"
                    )
                else:
                    unresolved.append("drink_buff_active requires a selected canonical drink")
                continue

            if condition in _ABILITY_OR_TRANSFORM_CONDITIONS:
                unresolved.append(
                    f"{condition} still requires an explicit slot/runtime materialization witness"
                )
                continue

            unresolved.append(f"Unreviewed Extreme resource runtime condition: {condition}")

        return ExtremeResourceRuntimeConditionState(
            objective_key=key,
            required_conditions=required,
            active_conditions=tuple(sorted(active, key=str.casefold)),
            unresolved_conditions=tuple(dict.fromkeys(unresolved)),
            evidence=tuple(dict.fromkeys(evidence)),
        )


__all__ = [
    "ExtremeResourceRuntimeConditionState",
    "ExtremeResourceRuntimeConditionStateService",
]
