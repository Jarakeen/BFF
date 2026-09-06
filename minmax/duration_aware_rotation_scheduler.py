from __future__ import annotations

from dataclasses import dataclass

from .rotation_plan import RotationAction, RotationActionKind, RotationPlan
from .rotation_recast import RotationRecastRule
from .rotation_wait_decision import (
    PrematureRecastDecisionContext,
    PrematureRecastDecisionProvider,
)


@dataclass(frozen=True)
class DurationAwareRotationScheduler:
    """Refine a valid semi-static plan using explicit duration evidence.

    Verified duration skills establish refresh obligations after their first cast.
    When an obligation becomes due, the next eligible skill slot on the same bar
    is claimed by that due ability. An explicit ``refresh_lead_seconds`` value on
    the verified rule moves that obligation into the supplied pre-expiry refresh
    window; zero lead preserves hard-expiry behavior.

    Existing timestamps and explicit bar swaps are preserved. When a refresh
    claims a same-bar skill slot, the displaced action cascades forward through
    later skill slots on that bar rather than being silently deleted. Any action
    still queued when the fixed plan horizon ends is reported explicitly.

    Premature recast slots that are not needed by another due refresh continue to
    use deterministic same-bar no-duration fillers when available. If no filler
    exists, an optional caller-proven decision provider may supply one legal action
    for that exact slot. Otherwise the slot becomes an explicit WAIT rather than
    an invented cast.

    The scheduler does not itself optimize bar-swap timing, pull a refresh onto the
    opposite bar, invent refresh lead windows, or infer execute, proc, potion,
    heavy-attack, sustain, or encounter legality. Those remain caller-owned Phase
    13 decision evidence.
    """

    def refine(
        self,
        plan: RotationPlan,
        rules: tuple[RotationRecastRule, ...],
        *,
        wait_decision: PrematureRecastDecisionProvider | None = None,
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
            "skills displaced by verified refresh obligations cascade to later same-bar skill slots"
        )
        assumptions.append(
            "explicit verified refresh lead windows are honored; no refresh lead is invented"
        )
        assumptions.append(
            "premature duration-skill recast slots use deterministic same-bar no-duration fillers when available"
        )
        if wait_decision is not None:
            assumptions.append(
                "caller-proven premature-recast decisions may replace waits without inventing legality"
            )

        actions: list[RotationAction] = []
        pending_light_attack: RotationAction | None = None
        displaced_by_bar: dict[str, list[RotationAction]] = {"front": [], "back": []}

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

            candidate = action
            queue = displaced_by_bar.get(action.bar or "")
            if queue:
                candidate = queue.pop(0)
                queue.append(action)

            candidate_key = (str(candidate.name or "").casefold(), action.bar)
            due_key = self._due_refresh(
                time_seconds=action.time_seconds,
                bar=action.bar,
                next_due=next_due,
                rule_order=rule_order,
                action_kind_by_key=action_kind_by_key,
            )

            if due_key is not None and due_key != candidate_key:
                due_rule = rule_map[due_key]
                due_kind = action_kind_by_key.get(due_key, RotationActionKind.SKILL)
                if queue is not None:
                    queue.insert(0, candidate)
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
                next_due[due_key] = self._refresh_due(action.time_seconds, due_rule)
                unresolved.append(
                    f"refresh obligation for '{due_rule.skill_name}' claimed the {action.time_seconds:g}s "
                    f"{action.bar or 'unknown'}-bar slot from '{candidate.name}'; displaced skill will "
                    "cascade to the next same-bar skill slot"
                )
                continue

            rule = rule_map.get(candidate_key)
            if rule is None:
                if pending_light_attack is not None:
                    actions.append(pending_light_attack)
                    pending_light_attack = None
                actions.append(self._at_slot(candidate, action))
                continue

            due = next_due.get(candidate_key)
            if due is None or action.time_seconds >= due:
                if pending_light_attack is not None:
                    actions.append(pending_light_attack)
                    pending_light_attack = None
                actions.append(self._at_slot(candidate, action))
                next_due[candidate_key] = self._refresh_due(action.time_seconds, rule)
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
                    f"premature recast of '{candidate.name}' at {action.time_seconds:g}s was replaced "
                    f"with same-bar filler '{replacement}'; exact priority ranking is unresolved"
                )
                continue

            decided_action = None
            if wait_decision is not None:
                decided_action = wait_decision(
                    PrematureRecastDecisionContext(
                        time_seconds=action.time_seconds,
                        bar=action.bar,
                        candidate=candidate,
                        slot=action,
                        next_due=tuple(
                            sorted(
                                (
                                    (name, bar, due_time)
                                    for (name, bar), due_time in next_due.items()
                                ),
                                key=lambda item: (item[2], item[1] or "", item[0]),
                            )
                        ),
                        rules=rules,
                    )
                )
                if decided_action is not None:
                    decided_action = self._validate_wait_decision(
                        decided_action,
                        slot=action,
                    )
                    pending_light_attack = None
                    actions.append(decided_action)
                    unresolved.append(
                        f"premature recast of '{candidate.name}' at {action.time_seconds:g}s was replaced "
                        f"by caller-proven {decided_action.kind.value} decision"
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
                f"premature recast of '{candidate.name}' at {action.time_seconds:g}s had no verified "
                f"same-bar no-duration filler or caller-proven replacement; scheduled wait instead"
            )

        if pending_light_attack is not None:
            actions.append(pending_light_attack)

        for bar, queued in displaced_by_bar.items():
            for displaced in queued:
                if displaced.name:
                    unresolved.append(
                        f"skill '{displaced.name}' was displaced beyond the {plan.duration_seconds:g}s "
                        f"plan horizon after same-bar refresh insertion on {bar} bar"
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
    def _validate_wait_decision(
        decided: RotationAction,
        *,
        slot: RotationAction,
    ) -> RotationAction:
        if decided.time_seconds != slot.time_seconds:
            raise ValueError("premature-recast replacement must use the decision slot timestamp")
        if decided.bar != slot.bar:
            raise ValueError("premature-recast replacement must remain on the active decision bar")
        if decided.kind in {RotationActionKind.BAR_SWAP, RotationActionKind.WAIT}:
            raise ValueError(
                "premature-recast replacement must be an already-proven active action, not bar_swap or wait"
            )
        return RotationAction(
            time_seconds=slot.time_seconds,
            sequence=slot.sequence,
            kind=decided.kind,
            name=decided.name,
            bar=slot.bar,
        )

    @staticmethod
    def _at_slot(candidate: RotationAction, slot: RotationAction) -> RotationAction:
        return RotationAction(
            time_seconds=slot.time_seconds,
            sequence=slot.sequence,
            kind=candidate.kind,
            name=candidate.name,
            bar=slot.bar,
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
    def _refresh_due(
        cast_time_seconds: float,
        rule: RotationRecastRule,
    ) -> float:
        return (
            float(cast_time_seconds)
            + rule.duration_seconds
            - rule.refresh_lead_seconds
        )

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
