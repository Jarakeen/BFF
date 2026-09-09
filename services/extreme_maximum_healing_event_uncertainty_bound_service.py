from __future__ import annotations

from dataclasses import dataclass

from services.extreme_dragon_blood_skill_component_repository import (
    ExtremeDragonBloodSkillComponentRepository,
)


@dataclass(frozen=True)
class ExtremeMaximumHealingEventUncertaintyBound:
    lower_bound: float | None
    upper_bound: float | None
    reason: str = ""

    @property
    def bounded(self) -> bool:
        return self.lower_bound is not None and self.upper_bound is not None


class ExtremeMaximumHealingEventUncertaintyBoundService:
    """Expose source-supported numeric intervals without inventing missing formulas.

    The current U50 Dragon Blood-family wording proves an increase of *up to* 50%
    based on missing Health, but does not prove the interpolation curve for the
    reworked Elder morph or whose missing-Health state governs its ally component.
    For maximum-event ranking this service therefore treats the already evaluated
    event as a lower bound and 1.5x that event as a strict source-supported ceiling.

    It does not mutate the canonical event value and does not mark the mechanic
    complete. The interval exists only to answer the pruning/proof question:
    could this unresolved family still overtake the current numeric leader?
    """

    MAX_MISSING_HEALTH_MULTIPLIER = 1.50
    _DRAGON_BLOOD_RANKS = frozenset(
        {
            ExtremeDragonBloodSkillComponentRepository.DRAGON_BLOOD_RANK_ID,
            ExtremeDragonBloodSkillComponentRepository.GREEN_DRAGON_BLOOD_RANK_ID,
            ExtremeDragonBloodSkillComponentRepository.ELDER_DRAGON_BLOOD_RANK_ID,
        }
    )

    def bound(self, entry) -> ExtremeMaximumHealingEventUncertaintyBound:
        value = getattr(entry, "event_value", None)
        if value is None:
            return ExtremeMaximumHealingEventUncertaintyBound(None, None)

        route_entry = getattr(entry, "route_entry", None)
        candidate = getattr(route_entry, "candidate", None)
        rank_id = getattr(candidate, "skill_rank_id", None)
        if rank_id is None or int(rank_id) not in self._DRAGON_BLOOD_RANKS:
            return ExtremeMaximumHealingEventUncertaintyBound(
                lower_bound=float(value),
                upper_bound=float(value),
            )

        return ExtremeMaximumHealingEventUncertaintyBound(
            lower_bound=float(value),
            upper_bound=float(value) * self.MAX_MISSING_HEALTH_MULTIPLIER,
            reason=(
                "reviewed Dragon Blood-family wording proves up to 50% additional "
                "healing from missing-Health scaling; exact interpolation remains unresolved"
            ),
        )
