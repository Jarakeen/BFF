from __future__ import annotations

"""Resolve whether the selected H1 heal can affect a target beyond a distance threshold.

Canonical ESO skill rows currently do not carry usable range geometry for the H1 heal
candidate set. This service therefore stays deliberately narrow: reviewed positive
controls may prove distant-target legality, canonical self-only HEAL identity may
prove a negative, and every other missing-range candidate remains unresolved.

The result is candidate-scoped so distance-conditioned gear can never become a
blanket character stat merely because the set is equipped.
"""

from dataclasses import dataclass
from pathlib import Path
import sqlite3

from minmax.skill_coefficient_repository import ability_entity_id
from minmax.skill_component_classification import HealRecipientScope, SkillEffectKind
from minmax.skill_component_repository import SkillComponentRepository
from services.extreme_dragon_blood_skill_component_repository import (
    ExtremeDragonBloodSkillComponentRepository,
)
from services.extreme_sorcerer_skill_component_repository import (
    ExtremeSorcererSkillComponentRepository,
)
from services.rotation_healer_u50_skill_component_repository import (
    RotationHealerU50SkillComponentRepository,
)


@dataclass(frozen=True)
class ExtremeActualHealCandidateDistanceResult:
    entity_id: str
    threshold_meters: float
    can_affect_target_beyond_threshold: bool | None
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()


class ExtremeActualHealCandidateDistanceService:
    """Fail-closed selected-heal distance witness for standing H1."""

    _REVIEWED_DISTANT_GROUND_HEALS = {
        "illustrious_healing": (
            28.0,
            8.0,
            "reviewed Illustrious Healing ground-target geometry",
        ),
        "budding_seeds": (
            28.0,
            8.0,
            "reviewed Budding Seeds ground-target geometry",
        ),
    }

    def __init__(
        self,
        database_path: str | Path,
        *,
        component_repository=None,
    ) -> None:
        self.database_path = Path(database_path)
        if component_repository is None:
            base = SkillComponentRepository(self.database_path)
            dragon = ExtremeDragonBloodSkillComponentRepository(
                self.database_path,
                base_repository=base,
            )
            sorcerer = ExtremeSorcererSkillComponentRepository(
                self.database_path,
                base_repository=dragon,
            )
            component_repository = RotationHealerU50SkillComponentRepository(
                self.database_path,
                base_repository=sorcerer,
            )
        self.components = component_repository

    def resolve(
        self,
        entity_id: str,
        *,
        threshold_meters: float,
    ) -> ExtremeActualHealCandidateDistanceResult:
        key = ability_entity_id(entity_id)
        threshold = float(threshold_meters)
        reviewed = self._REVIEWED_DISTANT_GROUND_HEALS.get(key)
        if reviewed is not None:
            placement_range, radius, source = reviewed
            can_reach = placement_range > threshold
            evidence = (
                f"{source}: placement_range={placement_range:g}m area_radius={radius:g}m; "
                f"selected heal can legally affect a target beyond {threshold:g}m",
            )
            return ExtremeActualHealCandidateDistanceResult(
                entity_id=key,
                threshold_meters=threshold,
                can_affect_target_beyond_threshold=can_reach,
                evidence=evidence,
            )

        rank = self._max_rank_for_entity(key)
        if rank is None:
            return ExtremeActualHealCandidateDistanceResult(
                entity_id=key,
                threshold_meters=threshold,
                can_affect_target_beyond_threshold=None,
                unresolved=(f"selected heal identity/rank is unavailable for {entity_id}",),
            )

        rank_id, name = rank
        heals = tuple(
            component
            for component in self.components.get_for_skill_rank(rank_id)
            if component.effect_kind is SkillEffectKind.HEAL
        )
        if heals and all(component.is_complete_heal_event_identity for component in heals):
            scopes = {component.heal_recipient_scope for component in heals}
            if scopes == {HealRecipientScope.SELF}:
                return ExtremeActualHealCandidateDistanceResult(
                    entity_id=key,
                    threshold_meters=threshold,
                    can_affect_target_beyond_threshold=False,
                    evidence=(
                        f"canonical HEAL identity for {name} is self-only; it cannot affect "
                        f"a target beyond {threshold:g}m",
                    ),
                )

        return ExtremeActualHealCandidateDistanceResult(
            entity_id=key,
            threshold_meters=threshold,
            can_affect_target_beyond_threshold=None,
            unresolved=(
                f"{name}: canonical range geometry does not prove whether the selected heal "
                f"can affect a target beyond {threshold:g}m",
            ),
        )

    def _max_rank_for_entity(self, entity_id: str) -> tuple[int, str] | None:
        if not entity_id or not self.database_path.exists():
            return None
        with sqlite3.connect(self.database_path) as connection:
            required = ("ability", "skill_rank")
            if any(
                connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                    (table,),
                ).fetchone()
                is None
                for table in required
            ):
                return None
            rows = connection.execute(
                """
                SELECT sr.id, COALESCE(sr.rank, 0), COALESCE(a.name, '')
                FROM skill_rank sr
                JOIN ability a ON a.ability_id = sr.ability_id
                WHERE COALESCE(a.is_player, 0) <> 0
                  AND COALESCE(a.is_passive, 0) = 0
                  AND COALESCE(a.name, '') <> ''
                """
            ).fetchall()
        matches = [
            (int(rank_id), int(rank or 0), str(name).strip())
            for rank_id, rank, name in rows
            if ability_entity_id(str(name)) == entity_id
        ]
        if not matches:
            return None
        rank_id, _rank, name = sorted(matches, key=lambda row: (-row[1], row[2].casefold(), row[0]))[0]
        return rank_id, name


__all__ = [
    "ExtremeActualHealCandidateDistanceResult",
    "ExtremeActualHealCandidateDistanceService",
]
