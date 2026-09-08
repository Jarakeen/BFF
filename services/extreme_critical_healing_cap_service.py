from __future__ import annotations

from dataclasses import dataclass, replace

from services.extreme_healing_event_service import ExtremeHealingEventResult


@dataclass(frozen=True)
class ExtremeCriticalHealingCapResult:
    event: ExtremeHealingEventResult
    effective_critical_bonus: float | None
    effective_critical_multiplier: float | None
    cap: float
    capped: bool


class ExtremeCriticalHealingCapService:
    """Apply ESO's Critical Healing ceiling without flattening mixed heal events.

    ``ExtremeHealingEventService`` stores ``critical_healing_bonus`` separately
    from the universal 50% base critical-healing bonus. ESO's ordinary cap is
    125% total critical-healing bonus, so the largest ordinary critical
    multiplier is 2.25x. Reviewed effects such as Nightblade ``Above and Beyond``
    may raise that bonus ceiling.

    This service can safely re-score mixed events where only some HEAL components
    may crit. It recovers the crit-eligible normal subtotal from the existing
    normal/critical pair instead of multiplying the whole finished event.
    """

    BASE_CRITICAL_HEALING = 0.50
    DEFAULT_CAP = 1.25

    def apply(
        self,
        event: ExtremeHealingEventResult,
        *,
        additional_critical_healing: float = 0.0,
        critical_healing_cap: float = DEFAULT_CAP,
    ) -> ExtremeCriticalHealingCapResult:
        cap = float(critical_healing_cap)
        if cap < self.BASE_CRITICAL_HEALING:
            raise ValueError("critical_healing_cap cannot be below base Critical Healing")

        additional = float(additional_critical_healing)
        if additional < 0.0:
            raise ValueError("additional_critical_healing cannot be negative")

        bonus = event.critical_healing_bonus
        if bonus is None:
            return ExtremeCriticalHealingCapResult(
                event=event,
                effective_critical_bonus=None,
                effective_critical_multiplier=None,
                cap=cap,
                capped=False,
            )

        raw_total_bonus = self.BASE_CRITICAL_HEALING + float(bonus) + additional
        effective_total_bonus = min(raw_total_bonus, cap)
        effective_bonus = max(0.0, effective_total_bonus - self.BASE_CRITICAL_HEALING)
        effective_multiplier = 1.0 + effective_total_bonus
        capped = effective_total_bonus < raw_total_bonus

        if event.normal_heal is None or event.critical_heal is None:
            adjusted = replace(
                event,
                critical_healing_bonus=effective_bonus,
                critical_multiplier=effective_multiplier,
            )
            return ExtremeCriticalHealingCapResult(
                event=adjusted,
                effective_critical_bonus=effective_bonus,
                effective_critical_multiplier=effective_multiplier,
                cap=cap,
                capped=capped,
            )

        old_multiplier = event.critical_multiplier
        if old_multiplier is None or float(old_multiplier) <= 1.0:
            unresolved = tuple(
                dict.fromkeys(
                    (*event.unresolved, "Critical Healing cap adjustment requires a valid prior critical multiplier")
                )
            )
            adjusted = replace(
                event,
                critical_heal=None,
                critical_healing_bonus=effective_bonus,
                critical_multiplier=effective_multiplier,
                unresolved=unresolved,
            )
            return ExtremeCriticalHealingCapResult(
                event=adjusted,
                effective_critical_bonus=effective_bonus,
                effective_critical_multiplier=effective_multiplier,
                cap=cap,
                capped=capped,
            )

        normal = float(event.normal_heal)
        critical = float(event.critical_heal)
        old_multiplier = float(old_multiplier)
        crit_eligible_normal = (critical - normal) / (old_multiplier - 1.0)
        noncrit_normal = normal - crit_eligible_normal

        # Floating-point reconstruction can produce microscopic negatives around
        # zero. Clamp only within numerical noise; meaningful negatives remain a
        # blocker because they imply an inconsistent event trace.
        epsilon = 1e-9
        if -epsilon < crit_eligible_normal < 0.0:
            crit_eligible_normal = 0.0
        if -epsilon < noncrit_normal < 0.0:
            noncrit_normal = 0.0
        if crit_eligible_normal < 0.0 or noncrit_normal < 0.0:
            unresolved = tuple(
                dict.fromkeys(
                    (*event.unresolved, "Critical Healing cap adjustment could not reconstruct crit-eligible heal subtotal")
                )
            )
            adjusted = replace(
                event,
                critical_heal=None,
                critical_healing_bonus=effective_bonus,
                critical_multiplier=effective_multiplier,
                unresolved=unresolved,
            )
        else:
            adjusted = replace(
                event,
                critical_heal=(crit_eligible_normal * effective_multiplier) + noncrit_normal,
                critical_healing_bonus=effective_bonus,
                critical_multiplier=effective_multiplier,
            )

        return ExtremeCriticalHealingCapResult(
            event=adjusted,
            effective_critical_bonus=effective_bonus,
            effective_critical_multiplier=effective_multiplier,
            cap=cap,
            capped=capped,
        )
