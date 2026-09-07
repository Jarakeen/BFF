from __future__ import annotations

from .duration_aware_rotation_scheduler import DurationAwareRotationScheduler
from .priority_aware_duration_scheduler import PriorityAwareDurationRotationScheduler
from .rotation_plan import RotationAction, RotationActionKind, RotationPlan
from .rotation_recast import RotationRecastRule
from .rotation_wait_decision import (
    PrematureRecastDecisionContext,
    PrematureRecastDecisionProvider,
)


class SoftActionDurationRotationScheduler(DurationAwareRotationScheduler):
    """Duration scheduler that lets proven runtime actions claim soft skill slots.

    The base duration scheduler asks a caller decision provider only after a
    premature recast has exhausted deterministic fillers and would otherwise become
    WAIT. That is intentionally conservative, but it can make a multi-slot action
    impossible by the time the WAIT seam arrives.

    This variant preserves the same hard boundaries and refresh obligations while
    exposing the provider one step earlier. A caller-proven action may replace:

    * a no-duration ordinary same-bar skill; or
    * a duration skill whose verified refresh is not yet due.

    First casts and due refreshes remain protected. When a soft no-duration skill is
    replaced, it is displaced into the same-bar queue and cascades forward through
    later soft slots instead of disappearing. Premature duration recasts need not be
    preserved because they are not refresh obligations.
    """

    def refine(
        self,
        plan: RotationPlan,
        rules: tuple[RotationRecastRule, ...],
        *,
        wait_decision: PrematureRecastDecisionProvider | None = None,
        soft_decision: PrematureRecastDecisionProvider | None = None,
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
        assumptions.extend(
            [
                "duration-aware refinement preserves existing action timestamps and explicit bar swaps",
                "verified refresh obligations may claim the next eligible skill slot on the same bar once due",
                "skills displaced by verified refresh obligations cascade to later same-bar skill slots",
                "explicit verified refresh lead windows are honored; no refresh lead is invented",
                "premature duration-skill recast slots use deterministic same-bar no-duration fillers when available",
            ]
        )
        if wait_decision is not None:
            assumptions.extend(
                [
                    "caller-proven premature-recast decisions may replace waits without inventing legality",
                    "verified channel reservations displace only ordinary same-bar skill decisions and never cross hard timeline boundaries",
                ]
            )
        if soft_decision is not None:
            assumptions.append(
                "caller-proven runtime decisions may claim soft same-bar skill slots after first-cast and due-refresh obligations are protected"
            )

        actions: list[RotationAction] = []
        pending_light_attack: RotationAction | None = None
        displaced_by_bar: dict[str, list[RotationAction]] = {"front": [], "back": []}
        reserved_until: float | None = None
        reserved_bar: str | None = None

        for action_index, action in enumerate(plan.actions):
            if reserved_until is not None and action.time_seconds >= reserved_until:
                reserved_until = None
                reserved_bar = None

            if reserved_until is not None and action.time_seconds < reserved_until:
                if action.kind is RotationActionKind.LIGHT_ATTACK:
                    continue
                if (
                    action.kind in {RotationActionKind.SKILL, RotationActionKind.ULTIMATE}
                    and action.bar == reserved_bar
                ):
                    if action.bar in displaced_by_bar:
                        displaced_by_bar[action.bar].append(action)
                    unresolved.append(
                        f"{action.kind.value} '{action.name or ''}' at {action.time_seconds:g}s was displaced by "
                        f"a verified channel reservation through {reserved_until:g}s on {reserved_bar} bar"
                    )
                    continue
                raise ValueError(
                    "verified channel reservation crossed a hard timeline boundary; "
                    f"encountered {action.kind.value} at {action.time_seconds:g}s before reservation end {reserved_until:g}s"
                )

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
            due = next_due.get(candidate_key) if rule is not None else None

            # A first cast or due refresh is not a soft decision. Preserve it before
            # consulting any caller runtime policy.
            if rule is not None and (due is None or action.time_seconds >= due):
                if pending_light_attack is not None:
                    actions.append(pending_light_attack)
                    pending_light_attack = None
                actions.append(self._at_slot(candidate, action))
                next_due[candidate_key] = self._refresh_due(action.time_seconds, rule)
                continue

            decided = self._decide(
                provider=soft_decision,
                plan=plan,
                rules=rules,
                action_index=action_index,
                action=action,
                candidate=candidate,
                next_due=next_due,
            )
            if decided is not None:
                decided_action, reservation_seconds, next_hard_boundary = decided
                if rule is None:
                    # Replacing a real ordinary action must displace it rather than
                    # silently deleting it. Premature duration recasts are optional
                    # repetitions and therefore do not enter the displaced queue.
                    target_queue = displaced_by_bar.get(action.bar or "")
                    if target_queue is not None:
                        target_queue.insert(0, candidate)
                reservation_end = action.time_seconds + reservation_seconds
                self._validate_channel_reservation(
                    reservation_end=reservation_end,
                    slot=action,
                    next_due=next_due,
                    next_hard_boundary_time_seconds=next_hard_boundary,
                    plan_end_seconds=plan.duration_seconds,
                )
                pending_light_attack = None
                actions.append(decided_action)
                if reservation_seconds > 0:
                    reserved_until = reservation_end
                    reserved_bar = action.bar
                unresolved.append(
                    f"soft {action.bar or 'unknown'}-bar decision at {action.time_seconds:g}s for "
                    f"'{candidate.name or ''}' was replaced by caller-proven {decided_action.kind.value} decision"
                )
                if reservation_seconds > 0:
                    unresolved.append(
                        f"caller-proven {decided_action.kind.value} at {action.time_seconds:g}s reserved "
                        f"the {action.bar or 'unknown'}-bar timeline through {reservation_end:g}s"
                    )
                continue

            if rule is None:
                if pending_light_attack is not None:
                    actions.append(pending_light_attack)
                    pending_light_attack = None
                actions.append(self._at_slot(candidate, action))
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

            wait_result = self._decide(
                provider=wait_decision,
                plan=plan,
                rules=rules,
                action_index=action_index,
                action=action,
                candidate=candidate,
                next_due=next_due,
            )
            if wait_result is not None:
                decided_action, reservation_seconds, next_hard_boundary = wait_result
                reservation_end = action.time_seconds + reservation_seconds
                self._validate_channel_reservation(
                    reservation_end=reservation_end,
                    slot=action,
                    next_due=next_due,
                    next_hard_boundary_time_seconds=next_hard_boundary,
                    plan_end_seconds=plan.duration_seconds,
                )
                pending_light_attack = None
                actions.append(decided_action)
                if reservation_seconds > 0:
                    reserved_until = reservation_end
                    reserved_bar = action.bar
                unresolved.append(
                    f"premature recast of '{candidate.name}' at {action.time_seconds:g}s was replaced "
                    f"by caller-proven {decided_action.kind.value} decision"
                )
                if reservation_seconds > 0:
                    unresolved.append(
                        f"caller-proven {decided_action.kind.value} at {action.time_seconds:g}s reserved "
                        f"the {action.bar or 'unknown'}-bar timeline through {reservation_end:g}s"
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
                        f"plan horizon after same-bar refresh/channel insertion on {bar} bar"
                    )

        return RotationPlan(
            character_name=plan.character_name,
            build_name=plan.build_name,
            duration_seconds=plan.duration_seconds,
            actions=tuple(actions),
            assumptions=tuple(self._dedupe(assumptions)),
            unresolved=tuple(self._dedupe(unresolved)),
        )

    def _decide(
        self,
        *,
        provider: PrematureRecastDecisionProvider | None,
        plan: RotationPlan,
        rules: tuple[RotationRecastRule, ...],
        action_index: int,
        action: RotationAction,
        candidate: RotationAction,
        next_due: dict[tuple[str, str | None], float],
    ):
        if provider is None:
            return None
        next_hard_boundary = self._next_hard_boundary_time(
            plan.actions,
            action_index,
            action.time_seconds,
            action.bar,
        )
        context = PrematureRecastDecisionContext(
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
            next_decision_time_seconds=self._next_decision_time(
                plan.actions,
                action_index,
                action.time_seconds,
            ),
            next_hard_boundary_time_seconds=next_hard_boundary,
            plan_end_seconds=plan.duration_seconds,
        )
        decided = provider(context)
        if decided is None:
            return None
        decided_action, reservation_seconds = self._normalize_wait_decision(
            decided,
            slot=action,
        )
        return decided_action, reservation_seconds, next_hard_boundary


class PriorityAwareSoftActionDurationRotationScheduler(
    SoftActionDurationRotationScheduler,
    PriorityAwareDurationRotationScheduler,
):
    """Soft-action scheduler retaining explicit priority ordering among due refreshes."""

    def __init__(self, priorities) -> None:
        PriorityAwareDurationRotationScheduler.__init__(self, priorities)
