from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExtremeHealingEventTemporalScopeResult:
    """Time-scope boundary for one reviewed healing ability.

    ``single_instant_safe`` answers whether BFF may safely treat all reviewed
    HEAL coefficient components as one healing event at one point in time for the
    Extreme Actual Heal objective. A false result does not mean the skill is
    invalid; it means direct-heal versus later-tick identity must be resolved
    before the skill can compete for a single-event maximum.
    """

    single_instant_safe: bool
    component_time_selection_required: bool
    unresolved: tuple[str, ...]


class ExtremeHealingEventTemporalScopeService:
    """Block reviewed direct-plus-HoT aggregation from becoming one giant heal.

    U50 ``Blood of the Green Dragon`` (legacy ``Green Dragon Blood``) has one
    immediate heal and an additional heal over time. The reviewed missing-Health
    bonus belongs to the immediate heal, while the current Extreme event layer
    does not yet retain a canonical timestamp/tick identity for each HEAL
    coefficient component. Summing all HEAL components would therefore answer
    "total healing represented by the cast" rather than "largest actual heal
    event".

    This is intentionally a reviewed guard, not a universal temporal classifier.
    Additional multi-time heal families should be added as their evidence is
    reviewed.
    """

    MULTI_TIME_DISTINCT_HEALING = frozenset(
        {
            "blood of the green dragon",
            "green dragon blood",
        }
    )

    @staticmethod
    def _normalized(value: object) -> str:
        return " ".join(str(value or "").strip().casefold().split())

    def resolve(self, *, ability_name: str) -> ExtremeHealingEventTemporalScopeResult:
        normalized = self._normalized(ability_name)
        if normalized not in self.MULTI_TIME_DISTINCT_HEALING:
            return ExtremeHealingEventTemporalScopeResult(
                single_instant_safe=True,
                component_time_selection_required=False,
                unresolved=(),
            )

        return ExtremeHealingEventTemporalScopeResult(
            single_instant_safe=False,
            component_time_selection_required=True,
            unresolved=(
                f"{ability_name}: one-event Extreme heal is unresolved because the "
                "reviewed cast contains an immediate heal plus later healing over "
                "time while canonical HEAL-component metadata does not identify "
                "which component is the immediate event versus later tick(s)",
            ),
        )
