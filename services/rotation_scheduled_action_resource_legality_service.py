from __future__ import annotations

from dataclasses import dataclass
import math
import re

from minmax.potion_cadence import BASE_POTION_COOLDOWN_SECONDS
from minmax.rotation_plan import RotationActionKind, RotationPlan
from minmax.ultimate_resource_timeline import UltimateGenerationEvent, UltimateSpendRule


@dataclass(frozen=True)
class RotationScheduledActionResourceViolation:
    action_kind: RotationActionKind
    action_name: str
    time_seconds: float
    reason: str


@dataclass(frozen=True)
class RotationScheduledActionResourceAssessment:
    violations: tuple[RotationScheduledActionResourceViolation, ...]
    unresolved: tuple[str, ...]
    starting_ultimate: float
    ending_ultimate: float
    potion_cooldown_seconds: float

    @property
    def is_legal(self) -> bool:
        return not self.violations and not self.unresolved


class RotationScheduledActionResourceLegalityService:
    """Validate resource/cooldown legality for scheduled Ultimates and potions.

    This service consumes explicit Ultimate generation events and explicit canonical
    Ultimate spend rules. It never infers generation from attacks, Heroism, sets,
    passives, or encounter state. Potion spacing defaults to the canonical base
    cooldown and accepts a caller-supplied effective cooldown only when another
    layer has resolved that modifier evidence.

    Same-timestamp Ultimate generation is not silently ordered ahead of a spend.
    If a cast would only become affordable by consuming generation at the exact
    same timestamp, affordability remains unresolved until sequencing evidence is
    available.
    """

    _EPSILON = 1e-9

    def assess(
        self,
        *,
        plan: RotationPlan,
        starting_ultimate: float = 0.0,
        ultimate_generation_events: tuple[UltimateGenerationEvent, ...] = (),
        ultimate_spend_rules: tuple[UltimateSpendRule, ...] = (),
        potion_cooldown_seconds: float = BASE_POTION_COOLDOWN_SECONDS,
    ) -> RotationScheduledActionResourceAssessment:
        starting = float(starting_ultimate)
        cooldown = float(potion_cooldown_seconds)
        if not math.isfinite(starting) or starting < 0.0:
            raise ValueError("starting Ultimate must be finite and non-negative")
        if not math.isfinite(cooldown) or cooldown <= 0.0:
            raise ValueError("potion cooldown must be finite and positive")

        rules = self._index_spend_rules(tuple(ultimate_spend_rules))
        events = tuple(
            sorted(
                ultimate_generation_events,
                key=lambda event: (event.time_seconds, event.source.casefold()),
            )
        )
        if any(event.time_seconds > plan.duration_seconds for event in events):
            raise ValueError("ultimate generation event cannot occur after rotation duration")

        balance = starting
        event_index = 0
        violations: list[RotationScheduledActionResourceViolation] = []
        unresolved: list[str] = []
        prior_potion_time: float | None = None

        relevant_actions = tuple(
            action
            for action in plan.actions
            if action.kind in {RotationActionKind.ULTIMATE, RotationActionKind.POTION}
        )

        for action in relevant_actions:
            while (
                event_index < len(events)
                and events[event_index].time_seconds < action.time_seconds - self._EPSILON
            ):
                balance += events[event_index].amount
                event_index += 1

            same_time_start = event_index
            while (
                event_index < len(events)
                and abs(events[event_index].time_seconds - action.time_seconds) <= self._EPSILON
            ):
                event_index += 1
            same_time_events = events[same_time_start:event_index]

            if action.kind is RotationActionKind.ULTIMATE:
                action_name = str(action.name or "").strip()
                rule = rules.get(self._stable_id(action_name))
                if rule is None:
                    unresolved.append(
                        f"scheduled Ultimate {action_name!r} at {action.time_seconds:.3f}s "
                        "has no explicit canonical spend rule"
                    )
                elif balance + self._EPSILON >= rule.cost:
                    balance -= rule.cost
                else:
                    same_time_gain = sum(event.amount for event in same_time_events)
                    if balance + same_time_gain + self._EPSILON >= rule.cost and same_time_events:
                        sources = ", ".join(event.source for event in same_time_events)
                        unresolved.append(
                            f"scheduled Ultimate {action_name!r} at {action.time_seconds:.3f}s "
                            f"is affordable only if same-timestamp generation occurs first: {sources}"
                        )
                    else:
                        violations.append(
                            RotationScheduledActionResourceViolation(
                                action_kind=action.kind,
                                action_name=action_name,
                                time_seconds=action.time_seconds,
                                reason=(
                                    f"requires {rule.cost:.3f} Ultimate but only "
                                    f"{balance:.3f} is available before the cast"
                                ),
                            )
                        )

            elif action.kind is RotationActionKind.POTION:
                action_name = str(action.name or "").strip()
                if prior_potion_time is not None:
                    gap = action.time_seconds - prior_potion_time
                    if gap + self._EPSILON < cooldown:
                        violations.append(
                            RotationScheduledActionResourceViolation(
                                action_kind=action.kind,
                                action_name=action_name,
                                time_seconds=action.time_seconds,
                                reason=(
                                    f"potion use occurs {gap:.3f}s after the prior use, "
                                    f"inside the {cooldown:.3f}s cooldown"
                                ),
                            )
                        )
                prior_potion_time = action.time_seconds

            for event in same_time_events:
                balance += event.amount

        while event_index < len(events):
            balance += events[event_index].amount
            event_index += 1

        return RotationScheduledActionResourceAssessment(
            violations=tuple(violations),
            unresolved=self._dedupe(tuple(unresolved)),
            starting_ultimate=starting,
            ending_ultimate=balance,
            potion_cooldown_seconds=cooldown,
        )

    @classmethod
    def _index_spend_rules(
        cls,
        rules: tuple[UltimateSpendRule, ...],
    ) -> dict[str, UltimateSpendRule]:
        indexed: dict[str, UltimateSpendRule] = {}
        for rule in rules:
            key = cls._stable_id(rule.skill_name)
            if key in indexed:
                raise ValueError(
                    f"duplicate Ultimate spend rule for {rule.skill_name!r}"
                )
            indexed[key] = rule
        return indexed

    @staticmethod
    def _stable_id(value: object) -> str:
        text = str(value or "").strip().casefold().replace("'", "")
        return re.sub(r"[^a-z0-9]+", "_", text).strip("_")

    @staticmethod
    def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            key = value.casefold()
            if key in seen:
                continue
            seen.add(key)
            result.append(value)
        return tuple(result)


__all__ = [
    "RotationScheduledActionResourceAssessment",
    "RotationScheduledActionResourceLegalityService",
    "RotationScheduledActionResourceViolation",
]
