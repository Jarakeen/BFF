from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .resource_costs import BaseActionCost, resolve_base_action_cost
from .skill_coefficient_repository import SkillCoefficientRepository


@dataclass(frozen=True)
class AbilityCostResolution:
    """Canonical action-cost lookup for one named ESO ability."""

    base_cost: BaseActionCost | None
    name: str
    skill_line: str | None
    unresolved: tuple[str, ...] = ()


class AbilityCostRepository:
    """Resolve a named skill into its canonical rank-specific resource cost.

    Skill identity/rank selection remains owned by ``SkillCoefficientRepository``.
    This repository only joins that resolved numeric ability ID back to the
    canonical ``ability`` row and promotes verified ``base_cost`` / resource
    mechanic fields into ``BaseActionCost``.
    """

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = str(database_path)
        self.skill_repository = SkillCoefficientRepository(database_path)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _table_exists(connection: sqlite3.Connection, name: str) -> bool:
        row = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (name,),
        ).fetchone()
        return row is not None

    def resolve_name(self, name: str) -> AbilityCostResolution:
        requested = str(name or "").strip()
        if not requested:
            return AbilityCostResolution(None, "", None, ("Skill name is required",))

        skill = self.skill_repository.resolve_name(requested)
        if skill.rank is None:
            return AbilityCostResolution(None, requested, None, skill.unresolved)

        resolved = skill.rank
        with self._connect() as connection:
            if not self._table_exists(connection, "ability"):
                return AbilityCostResolution(
                    None,
                    resolved.name,
                    None,
                    skill.unresolved + ("ability table is unavailable",),
                )
            row = connection.execute(
                """
                SELECT ability_id, base_cost, base_mechanic, skill_line
                FROM ability
                WHERE ability_id = ?
                """,
                (resolved.ability_id,),
            ).fetchone()

        if row is None:
            return AbilityCostResolution(
                None,
                resolved.name,
                None,
                skill.unresolved
                + (f"Ability cost row not found for source ability {resolved.ability_id}",),
            )

        base_cost = row["base_cost"]
        base_mechanic = row["base_mechanic"]
        if base_cost is None or float(base_cost) <= 0:
            return AbilityCostResolution(
                None,
                resolved.name,
                str(row["skill_line"] or "").strip() or None,
                skill.unresolved
                + (f"Ability {resolved.name} has no positive canonical base cost",),
            )
        if base_mechanic is None:
            return AbilityCostResolution(
                None,
                resolved.name,
                str(row["skill_line"] or "").strip() or None,
                skill.unresolved
                + (f"Ability {resolved.name} has no canonical resource mechanic",),
            )

        try:
            canonical = resolve_base_action_cost(
                ability_id=resolved.ability_id,
                base_cost=float(base_cost),
                base_mechanic=int(base_mechanic),
                rank=resolved.rank,
                morph=resolved.morph,
            )
        except ValueError as exc:
            return AbilityCostResolution(
                None,
                resolved.name,
                str(row["skill_line"] or "").strip() or None,
                skill.unresolved + (str(exc),),
            )

        return AbilityCostResolution(
            base_cost=canonical,
            name=resolved.name,
            skill_line=str(row["skill_line"] or "").strip() or None,
            unresolved=skill.unresolved,
        )
