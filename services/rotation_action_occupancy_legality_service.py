from __future__ import annotations

from dataclasses import dataclass
import math
import re

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan


@dataclass(frozen=True)
class RotationActionOccupancyRule:
    """Explicit timing evidence for one scheduled action family.

    Rules are caller-supplied evidence. This service does not invent ESO cast,
    channel, weave, or bar-swap timings. `action_name=None` applies to every action
    of the supplied kind; a named rule applies only to that stable action identity.
    `blocked_action_kinds` states which later scheduled action kinds cannot begin
    before this action's occupancy window ends.
    """

    action_kind: RotationActionKind
    occupancy_seconds: float
    blocked_action_kinds: tuple[RotationActionKind, ...]
    source: str
    action_name: str | None = None

    def __post_init__(self) -> None:
        try:
            kind = (
                self.action_kind
                if isinstance(self.action_kind, RotationActionKind)
                else RotationActionKind(str(self.action_kind))
            )
        except ValueError as exc:
            raise ValueError(f"unsupported occupancy action kind: {self.action_kind!r}") from exc
        object.__setattr__(self, "action_kind", kind)

        duration = float(self.occupancy_seconds)
        if not math.isfinite(duration) or duration < 0.0:
            raise ValueError("rotation action occupancy must be finite and non-negative")
        object.__setattr__(self, "occupancy_seconds", duration)

        source = str(self.source or "").strip()
        if not source:
            raise ValueError("rotation action occupancy rule requires a source")
        object.__setattr__(self, "source", source)

        name = str(self.action_name or "").strip()
        object.__setattr__(self, "action_name", name or None)

        blocked: list[RotationActionKind] = []
        seen: set[RotationActionKind] = set()
        for value in self.blocked_action_kinds:
            try:
                blocked_kind = (
                    value
                    if isinstance(value, RotationActionKind)
                    else RotationActionKind(str(value))
                )
            except ValueError as exc:
                raise ValueError(f"unsupported blocked action kind: {value!r}") from exc
            if blocked_kind in seen:
                continue
            seen.add(blocked_kind)
            blocked.append(blocked_kind)
        object.__setattr__(self, "blocked_action_kinds", tuple(blocked))


@dataclass(frozen=True)
class RotationActionOccupancyViolation:
    blocking_action: RotationAction
    blocked_action: RotationAction
    window_end_seconds: float
    source: str
    reason: str


@dataclass(frozen=True)
class RotationActionOccupancyAssessment:
    violations: tuple[RotationActionOccupancyViolation, ...]
    unresolved: tuple[str, ...]

    @property
    def is_legal(self) -> bool:
        return not self.violations and not self.unresolved


class RotationActionOccupancyLegalityService:
    """Validate explicit action occupancy windows against a RotationPlan.

    This layer is intentionally evidence-driven. It only constrains actions for
    which a unique occupancy rule is supplied. Missing rules mean "not evaluated",
    not zero duration. Multiple matching rules are unresolved rather than silently
    selecting one.
    """

    _EPSILON = 1e-9

    def assess(
        self,
        *,
        plan: RotationPlan,
        rules: tuple[RotationActionOccupancyRule, ...],
    ) -> RotationActionOccupancyAssessment:
        if not rules:
            return RotationActionOccupancyAssessment(violations=(), unresolved=())

        self._validate_rule_identity(rules)
        unresolved: list[str] = []
        resolved: list[tuple[RotationAction, RotationActionOccupancyRule]] = []

        for action in plan.actions:
            matches = tuple(rule for rule in rules if self._matches(rule, action))
            if len(matches) > 1:
                unresolved.append(
                    f"multiple rotation occupancy rules match {action.kind.value} "
                    f"{action.name!r} at {action.time_seconds:.3f}s"
                )
                continue
            if len(matches) == 1:
                resolved.append((action, matches[0]))

        violations: list[RotationActionOccupancyViolation] = []
        for action, rule in resolved:
            if rule.occupancy_seconds <= 0.0 or not rule.blocked_action_kinds:
                continue
            end = action.time_seconds + rule.occupancy_seconds
            for later in plan.actions:
                if not self._comes_after(action, later):
                    continue
                if later.time_seconds + self._EPSILON >= end:
                    break
                if later.kind not in rule.blocked_action_kinds:
                    continue
                violations.append(
                    RotationActionOccupancyViolation(
                        blocking_action=action,
                        blocked_action=later,
                        window_end_seconds=end,
                        source=rule.source,
                        reason=(
                            f"{later.kind.value} action begins at {later.time_seconds:.3f}s "
                            f"before the {action.kind.value} occupancy window ends at "
                            f"{end:.3f}s"
                        ),
                    )
                )

        return RotationActionOccupancyAssessment(
            violations=tuple(violations),
            unresolved=self._dedupe(tuple(unresolved)),
        )

    @classmethod
    def _matches(
        cls,
        rule: RotationActionOccupancyRule,
        action: RotationAction,
    ) -> bool:
        if rule.action_kind is not action.kind:
            return False
        if rule.action_name is None:
            return True
        return cls._stable_id(rule.action_name) == cls._stable_id(action.name)

    @classmethod
    def _validate_rule_identity(
        cls,
        rules: tuple[RotationActionOccupancyRule, ...],
    ) -> None:
        seen: set[tuple[RotationActionKind, str | None]] = set()
        for rule in rules:
            key = (
                rule.action_kind,
                None if rule.action_name is None else cls._stable_id(rule.action_name),
            )
            if key in seen:
                raise ValueError(
                    "duplicate rotation action occupancy rule for "
                    f"{rule.action_kind.value} {rule.action_name!r}"
                )
            seen.add(key)

    @staticmethod
    def _comes_after(first: RotationAction, second: RotationAction) -> bool:
        return (second.time_seconds, second.sequence) > (
            first.time_seconds,
            first.sequence,
        )

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
    "RotationActionOccupancyAssessment",
    "RotationActionOccupancyLegalityService",
    "RotationActionOccupancyRule",
    "RotationActionOccupancyViolation",
]
