from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .rotation_plan import RotationActionKind, RotationPlan


_SUPPORTED_ACTION_KINDS = frozenset(
    {
        RotationActionKind.SKILL,
        RotationActionKind.ULTIMATE,
        RotationActionKind.LIGHT_ATTACK,
        RotationActionKind.HEAVY_ATTACK,
    }
)
_NAMED_ACTION_KINDS = frozenset(
    {
        RotationActionKind.SKILL,
        RotationActionKind.ULTIMATE,
    }
)


class RotationTargetKind(str, Enum):
    """Explicit target identity supplied by canonical/caller evidence.

    This enum is intentionally independent from imported ESO integer target fields.
    No mapping from those opaque integers is assumed here.
    """

    SELF = "self"
    ALLY = "ally"
    ENEMY = "enemy"
    GROUND = "ground"
    CORPSE = "corpse"
    OBJECT = "object"


@dataclass(frozen=True)
class RotationActionTargetRequirement:
    """Allowed target identities for one scheduled action identity.

    Skills and Ultimates require an exact action name. Light/heavy attacks are
    matched by kind because RotationPlan does not assign them skill names.
    """

    allowed_targets: tuple[RotationTargetKind, ...]
    action_name: str | None = None
    action_kind: RotationActionKind = RotationActionKind.SKILL
    bar: str | None = None

    def __post_init__(self) -> None:
        try:
            kind = (
                self.action_kind
                if isinstance(self.action_kind, RotationActionKind)
                else RotationActionKind(str(self.action_kind))
            )
        except ValueError as exc:
            raise ValueError(
                f"unsupported rotation target action kind: {self.action_kind!r}"
            ) from exc
        if kind not in _SUPPORTED_ACTION_KINDS:
            raise ValueError(
                "rotation target requirements support skill, ultimate, light attack, or heavy attack actions"
            )
        object.__setattr__(self, "action_kind", kind)

        targets: list[RotationTargetKind] = []
        for raw in self.allowed_targets:
            try:
                target = raw if isinstance(raw, RotationTargetKind) else RotationTargetKind(str(raw))
            except ValueError as exc:
                raise ValueError(f"unsupported rotation target kind: {raw!r}") from exc
            if target not in targets:
                targets.append(target)
        if not targets:
            raise ValueError("rotation target requirement needs at least one allowed target")
        object.__setattr__(self, "allowed_targets", tuple(targets))

        name = str(self.action_name or "").strip()
        if kind in _NAMED_ACTION_KINDS:
            if not name:
                raise ValueError(
                    "rotation target requirement needs action_name for skill or ultimate"
                )
            object.__setattr__(self, "action_name", name)
        else:
            if name:
                raise ValueError(
                    "rotation weapon-attack target requirements are kind-identified and must not set action_name"
                )
            object.__setattr__(self, "action_name", None)

        if self.bar is not None:
            bar = str(self.bar).strip().casefold()
            if bar not in {"front", "back"}:
                raise ValueError("rotation target requirement bar must be front or back")
            object.__setattr__(self, "bar", bar)


@dataclass(frozen=True)
class RotationTargetStateWindow:
    """Explicit target identity available during one encounter-time window."""

    name: str
    start_seconds: float
    end_seconds: float
    target_kind: RotationTargetKind

    def __post_init__(self) -> None:
        name = str(self.name or "").strip()
        if not name:
            raise ValueError("rotation target-state window requires a name")
        object.__setattr__(self, "name", name)

        start = float(self.start_seconds)
        end = float(self.end_seconds)
        if start < 0.0:
            raise ValueError("rotation target-state start must be non-negative")
        if end <= start:
            raise ValueError("rotation target-state end must be after start")
        object.__setattr__(self, "start_seconds", start)
        object.__setattr__(self, "end_seconds", end)

        try:
            target = (
                self.target_kind
                if isinstance(self.target_kind, RotationTargetKind)
                else RotationTargetKind(str(self.target_kind))
            )
        except ValueError as exc:
            raise ValueError(
                f"unsupported rotation target-state kind: {self.target_kind!r}"
            ) from exc
        object.__setattr__(self, "target_kind", target)

    def contains(self, time_seconds: float) -> bool:
        value = float(time_seconds)
        return self.start_seconds <= value < self.end_seconds


@dataclass(frozen=True)
class RotationActionTargetViolation:
    requirement: RotationActionTargetRequirement
    window_name: str
    time_seconds: float
    observed_target: RotationTargetKind

    @property
    def reason(self) -> str:
        allowed = ", ".join(item.value for item in self.requirement.allowed_targets)
        return (
            f"observed target {self.observed_target.value!r} is not allowed; "
            f"expected one of: {allowed}"
        )


@dataclass(frozen=True)
class RotationActionTargetAssessment:
    violations: tuple[RotationActionTargetViolation, ...]

    @property
    def legal(self) -> bool:
        return not self.violations


class RotationActionTargetAssessor:
    """Audit scheduled actions against explicit target-state evidence.

    This layer does not infer target identity from tooltip text, role, action name,
    imported integer target fields, encounter name, or healing/damage intent.
    Requirements and target-state windows must both be supplied explicitly.
    """

    def assess(
        self,
        plan: RotationPlan,
        requirements: tuple[RotationActionTargetRequirement, ...],
        windows: tuple[RotationTargetStateWindow, ...],
    ) -> RotationActionTargetAssessment:
        self._validate_unique(requirements)
        normalized_windows = tuple(
            sorted(windows, key=lambda item: (item.start_seconds, item.end_seconds, item.name))
        )
        self._validate_nonoverlap(normalized_windows)
        violations: list[RotationActionTargetViolation] = []

        for requirement in requirements:
            wanted_name = (
                requirement.action_name.casefold()
                if requirement.action_name is not None
                else None
            )
            for action in plan.actions:
                if action.kind is not requirement.action_kind:
                    continue
                if wanted_name is not None:
                    if not action.name or str(action.name).casefold() != wanted_name:
                        continue
                if requirement.bar is not None and action.bar != requirement.bar:
                    continue

                window = next(
                    (item for item in normalized_windows if item.contains(action.time_seconds)),
                    None,
                )
                if window is None:
                    continue
                if window.target_kind in requirement.allowed_targets:
                    continue

                violations.append(
                    RotationActionTargetViolation(
                        requirement=requirement,
                        window_name=window.name,
                        time_seconds=float(action.time_seconds),
                        observed_target=window.target_kind,
                    )
                )

        return RotationActionTargetAssessment(tuple(violations))

    @staticmethod
    def _validate_unique(
        requirements: tuple[RotationActionTargetRequirement, ...],
    ) -> None:
        seen: set[tuple[RotationActionKind, str | None, str | None]] = set()
        for requirement in requirements:
            key = (
                requirement.action_kind,
                (
                    requirement.action_name.casefold()
                    if requirement.action_name is not None
                    else None
                ),
                requirement.bar,
            )
            if key in seen:
                label = requirement.action_name or requirement.action_kind.value
                raise ValueError(
                    "duplicate rotation target requirement for "
                    f"{label!r}"
                )
            seen.add(key)

    @staticmethod
    def _validate_nonoverlap(
        windows: tuple[RotationTargetStateWindow, ...],
    ) -> None:
        previous: RotationTargetStateWindow | None = None
        for window in windows:
            if previous is not None and window.start_seconds < previous.end_seconds:
                raise ValueError(
                    "target-state windows cannot overlap; combine encounter target state into one explicit window"
                )
            previous = window


__all__ = [
    "RotationActionTargetAssessment",
    "RotationActionTargetAssessor",
    "RotationActionTargetRequirement",
    "RotationActionTargetViolation",
    "RotationTargetKind",
    "RotationTargetStateWindow",
]
