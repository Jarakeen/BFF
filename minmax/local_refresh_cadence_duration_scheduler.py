from __future__ import annotations

from .duration_aware_rotation_scheduler import DurationAwareRotationScheduler
from .priority_aware_duration_scheduler import PriorityAwareDurationRotationScheduler
from .refresh_cadence_duration_scheduler import (
    RefreshCadenceDurationRotationScheduler,
    PriorityAwareRefreshCadenceDurationRotationScheduler,
    RotationRefreshIntervalPolicy,
)
from .rotation_plan import RotationAction, RotationActionKind, RotationPlan
from .rotation_recast import RotationRecastRule


class _LocalCadenceScopeMixin:
    """Limit cadence rescheduling to explicitly targeted skills.

    All verified duration skills remain protected from filler substitution, but only
    skills named by the supplied cadence policies are allowed to establish or satisfy
    refresh obligations during this refinement pass. Accepted seed-plan casts for
    unrelated duration skills keep their exact decision slots. If the ordinary
    displacement queue moves one, the local pass restores that protected slot and
    moves the occupying action forward into the displaced action's slot instead.
    """

    def _init_local_scope(
        self,
        refresh_cadences: tuple[RotationRefreshIntervalPolicy, ...],
        protected_duration_keys: tuple[tuple[str, str | None], ...],
    ) -> None:
        self._active_duration_keys = frozenset(
            (policy.skill_name.casefold(), policy.bar)
            for policy in tuple(refresh_cadences)
        )
        self._protected_duration_keys = frozenset(
            (str(name).casefold(), bar)
            for name, bar in tuple(protected_duration_keys)
        )
        self._protected_seed_slots: frozenset[tuple[float, str | None]] = frozenset()
        self._protected_seed_actions: tuple[RotationAction, ...] = ()

    def refine(
        self,
        plan: RotationPlan,
        rules: tuple[RotationRecastRule, ...],
        **kwargs,
    ) -> RotationPlan:
        protected_actions: list[RotationAction] = []
        for action in plan.actions:
            if action.kind not in {RotationActionKind.SKILL, RotationActionKind.ULTIMATE}:
                continue
            if not action.name:
                continue
            key = (action.name.casefold(), action.bar)
            if (
                key in self._protected_duration_keys
                and key not in self._active_duration_keys
            ):
                protected_actions.append(action)

        self._protected_seed_actions = tuple(protected_actions)
        self._protected_seed_slots = frozenset(
            (float(action.time_seconds), action.bar)
            for action in protected_actions
        )
        refined = super().refine(plan, rules, **kwargs)
        return self._restore_protected_seed_actions(refined)

    def _restore_protected_seed_actions(self, plan: RotationPlan) -> RotationPlan:
        actions = list(plan.actions)
        changed = False

        for protected in self._protected_seed_actions:
            if protected.name is None:
                continue

            exact = next(
                (
                    action
                    for action in actions
                    if action.time_seconds == protected.time_seconds
                    and action.kind is protected.kind
                    and action.name == protected.name
                    and action.bar == protected.bar
                ),
                None,
            )
            if exact is not None:
                continue

            protected_index = next(
                (
                    index
                    for index, action in enumerate(actions)
                    if action.kind is protected.kind
                    and action.name == protected.name
                    and action.bar == protected.bar
                    and action.time_seconds > protected.time_seconds
                ),
                None,
            )
            if protected_index is None:
                continue

            displaced_index = next(
                (
                    index
                    for index, action in enumerate(actions)
                    if action.time_seconds == protected.time_seconds
                    and action.sequence == protected.sequence
                ),
                None,
            )
            if displaced_index is None:
                continue

            moved_protected = actions[protected_index]
            displaced = actions[displaced_index]
            actions[displaced_index] = RotationAction(
                time_seconds=protected.time_seconds,
                sequence=protected.sequence,
                kind=moved_protected.kind,
                name=moved_protected.name,
                bar=protected.bar,
            )
            actions[protected_index] = RotationAction(
                time_seconds=moved_protected.time_seconds,
                sequence=moved_protected.sequence,
                kind=displaced.kind,
                name=displaced.name,
                bar=displaced.bar,
            )
            changed = True

        if not changed:
            return plan

        assumptions = tuple(
            dict.fromkeys(
                tuple(plan.assumptions)
                + (
                    "local cadence refinement restores accepted unrelated duration casts to their seed decision slots",
                )
            )
        )
        return RotationPlan(
            character_name=plan.character_name,
            build_name=plan.build_name,
            duration_seconds=plan.duration_seconds,
            actions=tuple(actions),
            assumptions=assumptions,
            unresolved=plan.unresolved,
        )

    def _due_refresh(
        self,
        *,
        time_seconds: float,
        bar: str | None,
        next_due: dict[tuple[str, str | None], float],
        rule_order: dict[tuple[str, str | None], int],
        action_kind_by_key: dict[tuple[str, str | None], RotationActionKind],
    ) -> tuple[str, str | None] | None:
        due_key = super()._due_refresh(
            time_seconds=time_seconds,
            bar=bar,
            next_due=next_due,
            rule_order=rule_order,
            action_kind_by_key=action_kind_by_key,
        )
        if due_key is None:
            return None
        if (float(time_seconds), bar) in self._protected_seed_slots:
            return None
        return due_key

    def _rule_map(
        self,
        rules: tuple[RotationRecastRule, ...],
    ) -> dict[tuple[str, str | None], RotationRecastRule]:
        full = DurationAwareRotationScheduler._rule_map(rules)
        return {
            key: rule
            for key, rule in full.items()
            if key in self._active_duration_keys
        }

    def _fillers(
        self,
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
            if key in self._protected_duration_keys:
                continue
            normalized = action.name.casefold()
            if normalized in seen[action.bar]:
                continue
            seen[action.bar].add(normalized)
            fillers[action.bar].append(action.name)
        return {bar: tuple(values) for bar, values in fillers.items()}


class LocalRefreshCadenceDurationRotationScheduler(
    _LocalCadenceScopeMixin,
    RefreshCadenceDurationRotationScheduler,
):
    """Non-priority local cadence scheduler preserving unrelated duration actions."""

    def __init__(
        self,
        refresh_cadences: tuple[RotationRefreshIntervalPolicy, ...],
        *,
        protected_duration_keys: tuple[tuple[str, str | None], ...],
    ) -> None:
        RefreshCadenceDurationRotationScheduler.__init__(self, refresh_cadences)
        self._init_local_scope(refresh_cadences, protected_duration_keys)


class PriorityAwareLocalRefreshCadenceDurationRotationScheduler(
    _LocalCadenceScopeMixin,
    PriorityAwareRefreshCadenceDurationRotationScheduler,
):
    """Priority-aware local cadence scheduler preserving unrelated duration actions."""

    def __init__(
        self,
        priorities,
        refresh_cadences: tuple[RotationRefreshIntervalPolicy, ...],
        *,
        protected_duration_keys: tuple[tuple[str, str | None], ...],
    ) -> None:
        PriorityAwareRefreshCadenceDurationRotationScheduler.__init__(
            self,
            priorities,
            refresh_cadences,
        )
        self._init_local_scope(refresh_cadences, protected_duration_keys)


__all__ = [
    "LocalRefreshCadenceDurationRotationScheduler",
    "PriorityAwareLocalRefreshCadenceDurationRotationScheduler",
]
