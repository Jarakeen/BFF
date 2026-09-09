from __future__ import annotations

from dataclasses import dataclass
import math

from minmax.rotation_plan import RotationPlan
from minmax.ultimate_generation_sources import CombatAttackUltimateGenerationSource
from services.rotation_lokkestiiz_landing_clock_service import LokkestiizLandingClockEvidence


@dataclass(frozen=True)
class LokkestiizHornLandingReadiness:
    occurrence: int
    landing_time_seconds: float
    amount_before_spend: float
    required_cost: float
    affordable: bool
    amount_after_spend: float


@dataclass(frozen=True)
class LokkestiizHornReadinessResult:
    starting_amount: float
    ending_amount: float
    landings: tuple[LokkestiizHornLandingReadiness, ...]
    generation_event_count: int
    unresolved: tuple[str, ...] = ()

    @property
    def ready(self) -> bool:
        return not self.unresolved and all(item.affordable for item in self.landings)


class RotationLokkestiizHornReadinessService:
    """Evaluate Aggressive Horn affordability at observed Lokkestiiz landings.

    Landing timestamps are pull/runtime evidence. Base-combat Ultimate generation is
    derived only from scheduled Light/Heavy Attacks when the caller explicitly says
    those attacks should count as successful damaging combat triggers.

    The service spends exactly one Horn cost at each landing when affordable and
    carries the remaining Ultimate forward. It does not convert health thresholds to
    seconds, infer starting Ultimate, infer Heroism, or invent attack success.
    """

    def __init__(
        self,
        generation_source: CombatAttackUltimateGenerationSource | None = None,
    ) -> None:
        self.generation_source = generation_source or CombatAttackUltimateGenerationSource()

    def evaluate(
        self,
        *,
        plan: RotationPlan,
        landing_clocks: LokkestiizLandingClockEvidence,
        starting_amount: float,
        horn_cost: float,
        assume_scheduled_attacks_damage: bool,
    ) -> LokkestiizHornReadinessResult:
        starting = float(starting_amount)
        cost = float(horn_cost)
        if not math.isfinite(starting) or starting < 0:
            raise ValueError("starting Ultimate must be finite and non-negative")
        if not math.isfinite(cost) or cost <= 0:
            raise ValueError("Aggressive Horn cost must be finite and greater than zero")

        unresolved: list[str] = list(landing_clocks.unresolved)
        if not landing_clocks.landing_times_seconds:
            unresolved.append("observed Lokkestiiz landing clocks are required")
            return LokkestiizHornReadinessResult(
                starting_amount=starting,
                ending_amount=starting,
                landings=(),
                generation_event_count=0,
                unresolved=tuple(unresolved),
            )

        last_landing = landing_clocks.landing_times_seconds[-1]
        if last_landing > plan.duration_seconds + 1e-9:
            unresolved.append(
                "rotation plan does not extend through the final observed Lokkestiiz landing: "
                f"plan={plan.duration_seconds:.3f}s, landing={last_landing:.3f}s"
            )
            return LokkestiizHornReadinessResult(
                starting_amount=starting,
                ending_amount=starting,
                landings=(),
                generation_event_count=0,
                unresolved=tuple(unresolved),
            )

        events = self.generation_source.events_from_plan(
            plan=plan,
            assume_scheduled_attacks_damage=assume_scheduled_attacks_damage,
        )
        if not assume_scheduled_attacks_damage:
            unresolved.append(
                "scheduled Light/Heavy Attacks are not proven successful damaging combat triggers"
            )

        balance = starting
        event_index = 0
        landings: list[LokkestiizHornLandingReadiness] = []

        for occurrence, landing_time in enumerate(
            landing_clocks.landing_times_seconds,
            start=1,
        ):
            while event_index < len(events) and events[event_index].time_seconds <= landing_time + 1e-9:
                balance += events[event_index].amount
                event_index += 1

            before = balance
            affordable = before + 1e-9 >= cost
            after = before - cost if affordable else before
            landings.append(
                LokkestiizHornLandingReadiness(
                    occurrence=occurrence,
                    landing_time_seconds=landing_time,
                    amount_before_spend=before,
                    required_cost=cost,
                    affordable=affordable,
                    amount_after_spend=after,
                )
            )
            balance = after

            if not affordable:
                unresolved.append(
                    "Aggressive Horn is not affordable at Lokkestiiz landing "
                    f"{occurrence}: available={before:.3f}, required={cost:.3f}, "
                    f"time={landing_time:.3f}s"
                )

        # Generation after the final landing is not relevant to the landing-readiness
        # proof and is intentionally excluded from ending_amount.
        return LokkestiizHornReadinessResult(
            starting_amount=starting,
            ending_amount=balance,
            landings=tuple(landings),
            generation_event_count=event_index,
            unresolved=tuple(unresolved),
        )


__all__ = [
    "LokkestiizHornLandingReadiness",
    "LokkestiizHornReadinessResult",
    "RotationLokkestiizHornReadinessService",
]
