from __future__ import annotations

from dataclasses import dataclass

from .rotation_plan import RotationAction, RotationActionKind, RotationPlan
from .rotation_recast import RotationRecastRule


@dataclass(frozen=True)
class DurationAwareRotationScheduler:
    """Refine a valid semi-static plan using explicit duration evidence.

    This first duration-aware slice deliberately preserves the plan's existing
    timestamps and explicit bar swaps. A duration-bearing skill is allowed on its
    first scheduled cast and again only once its verified duration has expired.
    Premature recast slots are filled by deterministic same-bar ordinary skills
    that do not themselves have duration rules. If no such filler exists, the
    slot becomes an explicit WAIT rather than an invented ability use.

    The scheduler does not yet pull recasts earlier/later than an existing action
    slot, optimize bar-swap timing, use refresh lead windows, or model execute,
    proc, potion, or encounter priorities. Those remain later Phase 13 work.
    """

    def refine(
        self,
        plan: RotationPlan,
        rules: tuple[RotationRecastRule, ...],
    ) -> RotationPlan:
        rule_map = self._rule_map(rules)
        filler_by_bar = self._fillers(plan, rule_map)
        filler_index = {"front": 0, "back": 0}
        next_due: dict[tuple[str, str | None], float] = {}
        unresolved = list(plan.unresolved)
        assumptions = list(plan.assumptions)
        assumptions.append(
            "duration-aware refinement preserves existing action timestamps and explicit bar swaps"
        )
        assumptions.append(
            "premature duration-skill recast slots use deterministic same-bar no-duration fillers when available"
        )

        actions: list[RotationAction] = []
        pending_light_attack: RotationAction | None = None

        for action in plan.actions:
            if action.kind is RotationActionKind.LIGHT_ATTACK:
                pending_light_attack = action
                continue

            if action.kind not in {RotationActionKind.SKILL, RotationActionKind.ULTIMATE}:
                if pending_light_attack is not None:
                    actions.append(pending_light_attack)
                    pending_light_attack = None
                actions.append(action)
                continue

            key = (str(action.name or "").casefold(), action.bar)
            rule = rule_map.get(key)
            if rule is None:
                if pending_light_attack is not None:
                    actions.append(pending_light_attack)
                    pending_light_attack = None
                actions.append(action)
                continue

            due = next_due.get(key)
            if due is None or action.time_seconds >= due:
                if pending_light_attack is not None:
                    actions.append(pending_light_attack)
                    pending_light_attack = None
                actions.append(action)
                next_due[key] = action.time_seconds + rule.duration_seconds
                continue

            replacement = self._next_filler(
                filler_by_bar=filler_by_bar,
                filler_index=filler_index,
                bar=action.bar,
            )
            if replacement is not None:
                if pending_light_attack is not None:
                    actions.append(pending_light_attack)
                    pending_light_attack = None
                actions.append(
                    RotationAction(
                        time_seconds=action.time_seconds,
                        sequence=action.sequence,
                        kind=RotationActionKind.SKILL,
                        name=replacement,
                        bar=action.bar,
                    )
                )
                unresolved.append(
                    f"premature recast of '{action.name}' at {action.time_seconds:g}s was replaced "
                    f"with same-bar filler '{replacement}'; exact priority ranking is unresolved"
                )
                continue

            pending_light_attack = None
            actions.append(
                RotationAction(
                    time_seconds=action.time_seconds,
                    sequence=0,
                    kind=RotationActionKind.WAIT,
                    name=None,
                    bar=action.bar,
                )
            )
            unresolved.append(
                f"premature recast of '{action.name}' at {action.time_seconds:g}s had no verified "
                f"same-bar no-duration filler; scheduled wait instead"
            )

        if pending_light_attack is not None:
            actions.append(pending_light_attack)

        return RotationPlan(
            character_name=plan.character_name,
            build_name=plan.build_name,
            duration_seconds=plan.duration_seconds,
            actions=tuple(actions),
            assumptions=tuple(self._dedupe(assumptions)),
            unresolved=tuple(self._dedupe(unresolved)),
        )

    @staticmethod
    def _rule_map(
        rules: tuple[RotationRecastRule, ...],
    ) -> dict[tuple[str, str | None], RotationRecastRule]:
        result: dict[tuple[str, str | None], RotationRecastRule] = {}
        for rule in rules:
            key = (rule.skill_name.casefold(), rule.bar)
            if key in result:
                raise ValueError(
                    f"duplicate duration-aware rule for {rule.skill_name!r} on {rule.bar or 'any'} bar"
                )
            result[key] = rule
        return result

    @staticmethod
    def _fillers(
        plan: RotationPlan,
        rule_map: dict[tuple[str, str | None], RotationRecastRule],
    ) -> dict[str, tuple[str, ...]]:
        fillers: dict[str, list[str]] = {"front": [], "back": []}
        seen: dict[str, set[str]] = {"front": set(), "back": set()}
        for action in plan.actions:
            if action.kind is not RotationActionKind.SKILL or not action.name:
                continue
            if action.bar not in fillers:
                continue
            key = (action.name.casefold(), action.bar)
            if key in rule_map:
                continue
            normalized = action.name.casefold()
            if normalized in seen[action.bar]:
                continue
            seen[action.bar].add(normalized)
            fillers[action.bar].append(action.name)
        return {bar: tuple(values) for bar, values in fillers.items()}

    @staticmethod
    def _next_filler(
        *,
        filler_by_bar: dict[str, tuple[str, ...]],
        filler_index: dict[str, int],
        bar: str | None,
    ) -> str | None:
        if bar not in filler_by_bar:
            return None
        values = filler_by_bar[bar]
        if not values:
            return None
        index = filler_index[bar] % len(values)
        filler_index[bar] += 1
        return values[index]

    @staticmethod
    def _dedupe(values: list[str]) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for raw in values:
            value = str(raw or "").strip()
            if not value:
                continue
            key = value.casefold()
            if key in seen:
                continue
            seen.add(key)
            ordered.append(value)
        return ordered
