from __future__ import annotations

"""Prove build/scenario-owned gear condition markers for standing Extreme H1 scoring.

This service owns no stat arithmetic and does not infer proc/runtime state. It
materializes conditions proven directly by the saved/hypothetical build plus the
standing H1 scenario itself: canonical provisioning kind, active-bar Destruction
Staff type, an explicitly selected transformed form, and ``standing_still``.
Pet, dodge, trigger, stack, and other runtime conditions remain absent until a
specialist runtime service proves them.
"""

from dataclasses import dataclass
from pathlib import Path
import sqlite3

from models.build_model import PlayerBuild


_DESTRUCTION_STAFF_TYPES = frozenset(
    {"inferno staff", "lightning staff", "ice staff", "destruction staff"}
)


@dataclass(frozen=True)
class ExtremeActualHealBuildConditionContext:
    active_conditions: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def condition_context(self) -> frozenset[str]:
        return frozenset(self.active_conditions)


class ExtremeActualHealBuildConditionContextService:
    """Resolve condition markers proven by the build or standing H1 scenario."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = str(database_path)
        self._provisioning_kind_cache: dict[str, str | None] = {}

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

    def resolve(
        self,
        build: PlayerBuild,
        *,
        active_bar: str = "front",
    ) -> ExtremeActualHealBuildConditionContext:
        active: set[str] = {"standing_still"}
        evidence: list[str] = ["standing_still: standing H1 scenario definition"]
        unresolved: list[str] = []

        food = str(build.Food or "").strip()
        if food:
            kind = self._provisioning_kind(food)
            if kind == "food":
                active.add("food_buff_active")
                evidence.append(f"food_buff_active: canonical provisioning type for {food}")
            elif kind == "drink":
                active.add("drink_buff_active")
                evidence.append(f"drink_buff_active: canonical provisioning type for {food}")
            else:
                unresolved.append(
                    f"Selected provisioning item has no canonical food/drink type: {food}"
                )

        main, _ = build.active_weapon_slots(active_bar)
        weapon_type = str(main.WeaponType or "").strip().casefold()
        if weapon_type in _DESTRUCTION_STAFF_TYPES:
            active.add("destruction_staff_equipped")
            evidence.append(
                f"destruction_staff_equipped: active weapon type is {weapon_type}"
            )

        transformed = str(build.TransformedForm or "").strip().casefold()
        if transformed:
            active.add("transformed")
            evidence.append(f"transformed: explicit build form is {transformed}")

        return ExtremeActualHealBuildConditionContext(
            active_conditions=tuple(sorted(active, key=str.casefold)),
            evidence=tuple(dict.fromkeys(evidence)),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )


__all__ = [
    "ExtremeActualHealBuildConditionContext",
    "ExtremeActualHealBuildConditionContextService",
]
