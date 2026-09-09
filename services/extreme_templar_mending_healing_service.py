from __future__ import annotations

from dataclasses import dataclass

from minmax.character_progression import CharacterProgression
from models.build_model import PlayerBuild
from services.extreme_heal_class_route_service import canonical_class_skill_line_id


@dataclass(frozen=True)
class ExtremeTemplarMendingHealingResult:
    multiplier: float
    healing_done_bonus: float
    passive_rank: int | None
    unresolved: tuple[str, ...]


class ExtremeTemplarMendingHealingService:
    """Resolve reviewed Templar Mending Healing Done for one heal target.

    Current Mending text grants generic Healing Done in proportion to the
    severity of the target's wounds: 6% at rank 1 and 13% at rank 2 at the
    maximum missing-Health condition. Extreme already requires an explicit
    target Health fraction for conditional one-event healing, so Mending can be
    evaluated deterministically without inventing an emergency-health state.

    The contribution belongs in the generic additive Healing Done bucket, not as
    an ability-family or final-output multiplier. Explicit subclass materialization
    is authoritative. A pure Templar may rely on its implicit native Restoring
    Light line; a subclassed/non-Templar build must explicitly carry that line.
    """

    PASSIVE_NAME = "Mending"
    RESTORING_LIGHT_ID = "restoring_light"
    BONUS_BY_RANK = {1: 0.06, 2: 0.13}

    @classmethod
    def _owns_restoring_light(cls, build: PlayerBuild) -> bool:
        explicit = {
            canonical_class_skill_line_id(value)
            for value in tuple(getattr(build, "ClassSkillLines", ()) or ())
            if canonical_class_skill_line_id(value)
        }
        if explicit:
            return cls.RESTORING_LIGHT_ID in explicit
        return str(getattr(build, "EsoClass", "") or "").strip().casefold() == "templar"

    def resolve(
        self,
        *,
        build: PlayerBuild,
        progression: CharacterProgression,
        target_health_fraction: float | None,
    ) -> ExtremeTemplarMendingHealingResult:
        if not self._owns_restoring_light(build):
            return ExtremeTemplarMendingHealingResult(1.0, 0.0, None, ())

        passive_ranks = getattr(progression, "passive_ranks", None)
        if passive_ranks is None:
            return ExtremeTemplarMendingHealingResult(
                1.0,
                0.0,
                None,
                ("Mending passive rank is not recorded",),
            )

        rank = progression.passive_rank(self.PASSIVE_NAME)
        if rank is None:
            return ExtremeTemplarMendingHealingResult(
                1.0,
                0.0,
                None,
                ("Passive rank is not recorded for character: Mending",),
            )
        rank = int(rank)
        if rank == 0:
            return ExtremeTemplarMendingHealingResult(1.0, 0.0, 0, ())
        if rank not in self.BONUS_BY_RANK:
            return ExtremeTemplarMendingHealingResult(
                1.0,
                0.0,
                rank,
                (f"Unsupported Mending passive rank: {rank}",),
            )

        if target_health_fraction is None:
            return ExtremeTemplarMendingHealingResult(
                1.0,
                0.0,
                rank,
                ("Mending requires explicit heal-target Health fraction",),
            )

        health = float(target_health_fraction)
        if not 0.0 <= health <= 1.0:
            raise ValueError("target_health_fraction must be between 0 and 1")

        bonus = self.BONUS_BY_RANK[rank] * (1.0 - health)
        return ExtremeTemplarMendingHealingResult(
            multiplier=1.0 + bonus,
            healing_done_bonus=bonus,
            passive_rank=rank,
            unresolved=(),
        )
