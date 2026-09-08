from __future__ import annotations

from dataclasses import dataclass
import math

from minmax.rotation_plan import RotationActionKind, RotationPlan
from minmax.ultimate_resource_timeline import UltimateGenerationEvent, UltimateSpendRule


@dataclass(frozen=True)
class RotationUltimateAffordabilityRequirement:
    """Explicit shared-Ultimate-pool evidence for final-plan legality.

    ``spend_rules`` contains only canonically resolved Ultimate identities/costs.
    ``generation_events`` contains only caller-proven Ultimate gains. The assessor
    never infers Heroism, attack generation, passives, sets, or encounter effects.
    """

    starting_amount: float
    spend_rules: tuple[UltimateSpendRule, ...]
    generation_events: tuple[UltimateGenerationEvent, ...] = ()

    def __post_init__(self) -> None:
        starting = float(self.starting_amount)
        if not math.isfinite(starting) or starting < 0.0:
            raise ValueError("starting Ultimate must be finite and non-negative")
        object.__setattr__(self, "starting_amount", starting)

        seen: dict[str, float] = {}
        for rule in self.spend_rules:
            key = rule.skill_name.casefold()
            prior = seen.get(key)
            if prior is not None and prior != rule.cost:
                raise ValueError(
                    "conflicting Ultimate costs for the same action identity: "
                    f"{rule.skill_name!r}"
                )
            seen[key] = rule.cost


@dataclass(frozen=True)
class RotationUltimateAffordabilityViolation:
    action_name: str
    time_seconds: float
    balance_before: float
    required_cost: float
    shortfall: float


@dataclass(frozen=True)
class RotationUltimateAffordabilityAssessment:
    starting_amount: float
    ending_amount: float
    applied_generation_events: tuple[UltimateGenerationEvent, ...]
    violations: tuple[RotationUltimateAffordabilityViolation, ...]

    @property
    def satisfied(self) -> bool:
        return not self.violations


class RotationUltimateAffordabilityAssessor:
    """Replay explicit Ultimate generation against a final candidate plan.

    Generation at the same timestamp is applied before an Ultimate spend, matching
    ``UltimateResourceTimeline`` availability semantics. Multiple Ultimate actions
    at the same timestamp then consume the shared pool in deterministic plan order.
    An unaffordable scheduled cast is reported but does not spend resources because
    the cast is not legal.
    """

    def assess(
        self,
        plan: RotationPlan,
        requirement: RotationUltimateAffordabilityRequirement,
    ) -> RotationUltimateAffordabilityAssessment:
        if any(event.time_seconds > plan.duration_seconds for event in requirement.generation_events):
            raise ValueError("ultimate generation event cannot occur after plan duration")

        rules = {
            rule.skill_name.casefold(): rule
            for rule in requirement.spend_rules
        }
        events = tuple(
            sorted(
                requirement.generation_events,
                key=lambda event: (event.time_seconds, event.source.casefold()),
            )
        )
        balance = float(requirement.starting_amount)
        event_index = 0
        applied: list[UltimateGenerationEvent] = []
        violations: list[RotationUltimateAffordabilityViolation] = []

        for action in plan.actions:
            if action.kind is not RotationActionKind.ULTIMATE:
                continue

            at_time = float(action.time_seconds)
            while event_index < len(events) and events[event_index].time_seconds <= at_time:
                event = events[event_index]
                balance += event.amount
                applied.append(event)
                event_index += 1

            name = str(action.name or "").strip()
            rule = rules.get(name.casefold()) if name else None
            if rule is None:
                continue

            before = balance
            if before + 1e-9 < rule.cost:
                violations.append(
                    RotationUltimateAffordabilityViolation(
                        action_name=name,
                        time_seconds=at_time,
                        balance_before=before,
                        required_cost=rule.cost,
                        shortfall=rule.cost - before,
                    )
                )
                continue

            balance -= rule.cost

        while event_index < len(events):
            event = events[event_index]
            balance += event.amount
            applied.append(event)
            event_index += 1

        return RotationUltimateAffordabilityAssessment(
            starting_amount=requirement.starting_amount,
            ending_amount=balance,
            applied_generation_events=tuple(applied),
            violations=tuple(violations),
        )


__all__ = [
    "RotationUltimateAffordabilityAssessment",
    "RotationUltimateAffordabilityAssessor",
    "RotationUltimateAffordabilityRequirement",
    "RotationUltimateAffordabilityViolation",
]
