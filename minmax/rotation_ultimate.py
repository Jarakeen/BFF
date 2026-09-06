from __future__ import annotations

from dataclasses import dataclass
import math

from .rotation_plan import RotationAction, RotationActionKind, RotationPlan


@dataclass(frozen=True)
class UltimateScheduleRule:
    """Explicit evidence required to place one ultimate in a rotation plan.

    ``cost`` is canonical ability-cost evidence. ``available_at_seconds`` is an
    externally supplied runtime/generation fact; Phase 13 does not infer it from
    class, light attacks, Heroism, Decisive, encounter length, or folklore.
    """

    skill_name: str
    bar: str
    cost: float
    available_at_seconds: tuple[float, ...]

    def __post_init__(self) -> None:
        name = str(self.skill_name or "").strip()
        if not name:
            raise ValueError("ultimate schedule rule requires a skill name")
        object.__setattr__(self, "skill_name", name)

        bar = str(self.bar or "").strip().casefold()
        if bar not in {"front", "back"}:
            raise ValueError("ultimate schedule rule bar must be 'front' or 'back'")
        object.__setattr__(self, "bar", bar)

        cost = float(self.cost)
        if not math.isfinite(cost) or cost <= 0:
            raise ValueError("ultimate schedule rule cost must be finite and greater than zero")
        object.__setattr__(self, "cost", cost)

        availability = tuple(float(value) for value in self.available_at_seconds)
        if any(not math.isfinite(value) or value < 0 for value in availability):
            raise ValueError("ultimate availability times must be finite and non-negative")
        if tuple(sorted(availability)) != availability:
            raise ValueError("ultimate availability times must be ordered")
        object.__setattr__(self, "available_at_seconds", availability)


class UltimateRotationScheduler:
    """Place explicitly available ultimates into eligible same-bar action slots.

    This first slice preserves all existing timestamps and bar swaps. Each supplied
    availability time may claim the first SKILL slot on the matching bar at or
    after that time. Availability that cannot be placed remains explicit unresolved
    evidence. The scheduler never invents Ultimate generation or availability.
    """

    def apply(
        self,
        plan: RotationPlan,
        rules: tuple[UltimateScheduleRule, ...],
    ) -> RotationPlan:
        self._validate_rules(rules)
        pending: list[tuple[float, int, UltimateScheduleRule]] = []
        for rule_index, rule in enumerate(rules):
            for available_at in rule.available_at_seconds:
                pending.append((available_at, rule_index, rule))
        pending.sort(key=lambda item: (item[0], item[1], item[2].skill_name.casefold()))

        actions: list[RotationAction] = []
        unresolved = list(plan.unresolved)
        assumptions = list(plan.assumptions)
        assumptions.append(
            "ultimate placement uses only explicitly supplied availability times and canonical costs"
        )
        assumptions.append(
            "ultimate scheduling preserves existing timestamps and explicit bar swaps"
        )

        used: set[int] = set()
        for action in plan.actions:
            if action.kind is not RotationActionKind.SKILL:
                actions.append(action)
                continue

            selected_index = None
            selected_rule = None
            for index, (available_at, _rule_index, rule) in enumerate(pending):
                if index in used:
                    continue
                if rule.bar != action.bar:
                    continue
                if available_at > action.time_seconds:
                    continue
                selected_index = index
                selected_rule = rule
                break

            if selected_rule is None:
                actions.append(action)
                continue

            used.add(selected_index)
            actions.append(
                RotationAction(
                    time_seconds=action.time_seconds,
                    sequence=action.sequence,
                    kind=RotationActionKind.ULTIMATE,
                    name=selected_rule.skill_name,
                    bar=action.bar,
                )
            )
            unresolved.append(
                f"ultimate '{selected_rule.skill_name}' claimed the {action.time_seconds:g}s "
                f"{action.bar}-bar slot from '{action.name}'; displaced-action priority is unresolved"
            )

        for index, (available_at, _rule_index, rule) in enumerate(pending):
            if index in used:
                continue
            unresolved.append(
                f"ultimate '{rule.skill_name}' became explicitly available at {available_at:g}s "
                f"but no eligible {rule.bar}-bar skill slot remained"
            )

        return RotationPlan(
            character_name=plan.character_name,
            build_name=plan.build_name,
            duration_seconds=plan.duration_seconds,
            actions=tuple(actions),
            assumptions=tuple(self._dedupe(assumptions)),
            unresolved=tuple(self._dedupe(unresolved)),
        )

    @staticmethod
    def _validate_rules(rules: tuple[UltimateScheduleRule, ...]) -> None:
        seen: set[tuple[str, str]] = set()
        for rule in rules:
            key = (rule.skill_name.casefold(), rule.bar)
            if key in seen:
                raise ValueError(
                    f"duplicate ultimate schedule rule for {rule.skill_name!r} on {rule.bar} bar"
                )
            seen.add(key)

    @staticmethod
    def _dedupe(values: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for raw in values:
            value = str(raw or "").strip()
            if not value:
                continue
            key = value.casefold()
            if key in seen:
                continue
            seen.add(key)
            result.append(value)
        return result
