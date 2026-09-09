from __future__ import annotations

from .duration_aware_rotation_scheduler import DurationAwareRotationScheduler
from .priority_aware_duration_scheduler import PriorityAwareDurationRotationScheduler
from .refresh_cadence_duration_scheduler import (
    RefreshCadenceDurationRotationScheduler,
    PriorityAwareRefreshCadenceDurationRotationScheduler,
    RotationRefreshIntervalPolicy,
)
from .rotation_plan import RotationActionKind, RotationPlan
from .rotation_recast import RotationRecastRule


class _LocalCadenceScopeMixin:
    """Limit cadence rescheduling to explicitly targeted skills.

    All verified duration skills remain protected from filler substitution, but only
    skills named by the supplied cadence policies are allowed to establish or satisfy
    refresh obligations during this refinement pass. This preserves an already-
    accepted seed schedule for unrelated duration skills unless the new local cadence
    actually displaces one of their timeline slots.
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
