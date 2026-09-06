from __future__ import annotations

from dataclasses import dataclass

from .rotation_plan import RotationAction, RotationActionKind, RotationPlan
from .rotation_recast import RotationRecastRule


@dataclass(frozen=True)
class DurationAwareRotationScheduler:
    """Refine a valid semi-static plan using explicit duration evidence.

    Verified duration skills establish refresh obligations after their first cast.
    When an obligation becomes due, the next eligible skill slot on the same bar
    is claimed by that due ability. Existing timestamps and explicit bar swaps are
    still preserved in this Phase 13 slice; the displaced ordinary cast is not
    silently moved elsewhere.

    Premature recast slots that are not needed by another due refresh continue to
    use deterministic same-bar no-duration fillers when available. If no valid
    filler exists, the slot becomes an explicit WAIT rather than an invented cast.

    The scheduler does not yet optimize bar-swap timing, pull a refresh onto the
    opposite bar, use refresh lead windows, or model execute, proc, potion, or
    encounter priorities. Those remain later Phase 13 work.
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
        action_kind_by_key = self._action_kinds(plan)
        rule_order = {
            (rule.skill_name.casefold(), rule.bar): index
            for index, rule in enumerate(rules)
        }
        unresolved = list(plan.unresolved)
        assumptions = list(plan.assumptions)
        assumptions.append(
            "duration-aware refinement preserves existing action timestamps and explicit bar swaps"
        )
        assumptions.append(
            "verified refresh obligations may claim the next eligible skill slot on the same bar once due"
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

            planned_key = (str(action.name or "").casefold(), action.bar)
            due_key = self._due_refresh(
                time_seconds=action.time_seconds,
                bar=action.bar,
                next_due=next_due,
                rule_order=rule_order,
                action_kind_by_key=action_kind_by_key,
            )

            if due_key is not None and due_key != planned_key:
                due_rule = rule_map[due_key]
                due_kind = action_kind_by_key.get(due_key, RotationActionKind.SKILL)
                if pending_light_attack is not None:
                    actions.append(pending_light_attack)
                    pending_light_attack = None
                actions.append(
                    RotationAction(
                        time_seconds=action.time_seconds,
                        sequence=action.sequence,
                        kind=due_kind,
                        name=due_rule.skill_name,
                        bar=action.bar,
                    )
                )
                next_due[due_key] = action.time_seconds + due_rule.duration_seconds
                unresolved.append(
                    f"refresh obligation for '{due_rule.skill_name}' claimed the {action.time_seconds:g}s "
                    f"{action.bar or 'unknown'}-bar slot from '{action.name}'; displaced-action priority is unresolved"
                )
                continue

            rule = rule_map.get(planned_key)
            if rule is None:
                if pending_light_attack is not None:
                    actions.append(pending_light_attack)
                    pending_light_attack = None
                actions.append(action)
                continue

            due = next_due.get(planned_key)
            if due is None or action.time_seconds >= due:
                if pending_light_attack is not None:
                    actions.append(pending_light_attack)
                    pending_light_attack = None
                actions.append(action)
                next_due[planned_key] = action.time_seconds + rule.duration_seconds
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
    def _validate_rule_key(rule: RotationRecastRule) -> tuple[str, str | None]:
        return (rule.skill_name.casefold(), rule.bar)

    @classmethod
    def _rule_map(
        cls,
        rules: tuple[RotationRecastRule, ...],
    ) -> dict[tuple[str, str | None], RotationRecastRule]:
        result: dict[tuple[str, str | None], RotationRecastRule] = {}
        for rule in rules:
            key = cls._validate_rule_key(rule)
            if key in result:
                raise ValueError(
                    f"duplicate duration-aware rule for {rule.skill_name!r} on {rule.bar or 'any'} bar"
                )
            result[key] = rule
        return result

    @staticmethod
    def _action_kinds(
        plan: RotationPlan,
    ) -> dict[tuple[str, str | None], RotationActionKind]:
        result: dict[tuple[str, str | None], RotationActionKind] = {}
        for action in plan.actions:
            if action.kind not in {RotationActionKind.SKILL, RotationActionKind.ULTIMATE}:
                continue
            if not action.name:
                continue
            key = (action.name.casefold(), action.bar)
            result.setdefault(key, action.kind)
        return result

    @staticmethod
    def _due_refresh(
        *,
        time_seconds: float,
        bar: str | None,
        next_due: dict[tuple[str, str | None], float],
        rule_order: dict[tuple[str, str | None], int],
        action_kind_by_key: dict[tuple[str, str | None], RotationActionKind],
    ) -> tuple[str, str | None] | None:
        candidates = [
            (due, rule_order.get(key, 10**9), key)
            for key, due in next_due.items()
            if key[1] == bar
            and due <= time_seconds
            and action_kind_by_key.get(key) is RotationActionKind.SKILL
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda item: (item[0], item[1], item[2][0]))
        return candidates[0][2]

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
