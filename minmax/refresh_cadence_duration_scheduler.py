from __future__ import annotations

from dataclasses import dataclass
import math

from .duration_aware_rotation_scheduler import DurationAwareRotationScheduler
from .priority_aware_duration_scheduler import PriorityAwareDurationRotationScheduler
from .rotation_recast import RotationRecastRule
from .soft_action_duration_scheduler import (
    PriorityAwareSoftActionDurationRotationScheduler,
    SoftActionDurationRotationScheduler,
)


@dataclass(frozen=True)
class RotationRefreshIntervalPolicy:
    """Explicit caller strategy for one verified duration skill's recast interval.

    ``interval_seconds`` is schedule policy, not canonical ESO duration evidence.
    The policy may deliberately exceed the verified effect duration when an
    encounter-scoped uptime target permits a gap. Earlier-than-expiry recasts remain
    represented by the existing verified refresh-lead mechanism rather than by this
    policy type.
    """

    skill_name: str
    interval_seconds: float
    bar: str | None = None
    source: str = "strategy"

    def __post_init__(self) -> None:
        name = str(self.skill_name or "").strip()
        if not name:
            raise ValueError("refresh interval policy requires a skill name")
        object.__setattr__(self, "skill_name", name)

        interval = float(self.interval_seconds)
        if not math.isfinite(interval) or interval <= 0.0:
            raise ValueError("refresh interval policy must be finite and positive")
        object.__setattr__(self, "interval_seconds", interval)

        if self.bar is not None:
            bar = str(self.bar).strip().casefold()
            if bar not in {"front", "back"}:
                raise ValueError("refresh interval policy bar must be 'front' or 'back'")
            object.__setattr__(self, "bar", bar)

        source = str(self.source or "").strip()
        if not source:
            raise ValueError("refresh interval policy source is required")
        object.__setattr__(self, "source", source)


class _RefreshCadenceDueMixin:
    def _init_refresh_cadences(
        self,
        refresh_cadences: tuple[RotationRefreshIntervalPolicy, ...],
    ) -> None:
        cadence_map: dict[tuple[str, str | None], RotationRefreshIntervalPolicy] = {}
        for policy in tuple(refresh_cadences):
            key = (policy.skill_name.casefold(), policy.bar)
            if key in cadence_map:
                raise ValueError(
                    f"duplicate refresh interval policy for {policy.skill_name!r} on "
                    f"{policy.bar or 'any'} bar"
                )
            cadence_map[key] = policy
        self._refresh_cadence_map = cadence_map

    def refine(
        self,
        plan,
        rules: tuple[RotationRecastRule, ...],
        **kwargs,
    ):
        self._validate_refresh_cadences(rules)
        return super().refine(plan, rules, **kwargs)

    def _validate_refresh_cadences(
        self,
        rules: tuple[RotationRecastRule, ...],
    ) -> None:
        rule_map = {
            (rule.skill_name.casefold(), rule.bar): rule
            for rule in tuple(rules)
        }
        for key, policy in self._refresh_cadence_map.items():
            rule = rule_map.get(key)
            if rule is None:
                raise ValueError(
                    f"refresh interval policy for {policy.skill_name!r} on "
                    f"{policy.bar or 'any'} bar has no verified duration rule"
                )
            if rule.refresh_lead_seconds > 1e-9:
                raise ValueError(
                    f"refresh interval policy for {policy.skill_name!r} conflicts with "
                    "an existing verified early-refresh lead"
                )
            if policy.interval_seconds + 1e-9 < rule.duration_seconds:
                raise ValueError(
                    f"refresh interval policy for {policy.skill_name!r} is earlier than "
                    "verified expiry; use the refresh-lead policy for intentional overlap"
                )

    def _refresh_due(
        self,
        cast_time_seconds: float,
        rule: RotationRecastRule,
    ) -> float:
        policy = self._refresh_cadence_map.get(
            (rule.skill_name.casefold(), rule.bar)
        )
        if policy is None:
            return super()._refresh_due(cast_time_seconds, rule)
        return float(cast_time_seconds) + float(policy.interval_seconds)


class RefreshCadenceDurationRotationScheduler(
    _RefreshCadenceDueMixin,
    DurationAwareRotationScheduler,
):
    """Duration scheduler honoring explicit at/after-expiry cadence policy."""

    def __init__(
        self,
        refresh_cadences: tuple[RotationRefreshIntervalPolicy, ...],
    ) -> None:
        self._init_refresh_cadences(tuple(refresh_cadences))


class PriorityAwareRefreshCadenceDurationRotationScheduler(
    _RefreshCadenceDueMixin,
    PriorityAwareDurationRotationScheduler,
):
    """Priority-aware duration scheduler with explicit refresh cadence policy."""

    def __init__(
        self,
        priorities,
        refresh_cadences: tuple[RotationRefreshIntervalPolicy, ...],
    ) -> None:
        PriorityAwareDurationRotationScheduler.__init__(self, priorities)
        self._init_refresh_cadences(tuple(refresh_cadences))


class RefreshCadenceSoftActionDurationRotationScheduler(
    _RefreshCadenceDueMixin,
    SoftActionDurationRotationScheduler,
):
    """Soft-action duration scheduler with explicit refresh cadence policy."""

    def __init__(
        self,
        refresh_cadences: tuple[RotationRefreshIntervalPolicy, ...],
    ) -> None:
        self._init_refresh_cadences(tuple(refresh_cadences))


class PriorityAwareRefreshCadenceSoftActionDurationRotationScheduler(
    _RefreshCadenceDueMixin,
    PriorityAwareSoftActionDurationRotationScheduler,
):
    """Priority/soft-action scheduler with explicit refresh cadence policy."""

    def __init__(
        self,
        priorities,
        refresh_cadences: tuple[RotationRefreshIntervalPolicy, ...],
    ) -> None:
        PriorityAwareSoftActionDurationRotationScheduler.__init__(self, priorities)
        self._init_refresh_cadences(tuple(refresh_cadences))


__all__ = [
    "PriorityAwareRefreshCadenceDurationRotationScheduler",
    "PriorityAwareRefreshCadenceSoftActionDurationRotationScheduler",
    "RefreshCadenceDurationRotationScheduler",
    "RefreshCadenceSoftActionDurationRotationScheduler",
    "RotationRefreshIntervalPolicy",
]
