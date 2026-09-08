from __future__ import annotations

from dataclasses import dataclass

from .rotation_plan import RotationActionKind, RotationPlan


_SUPPORTED_KINDS = frozenset({
    RotationActionKind.SKILL,
    RotationActionKind.ULTIMATE,
})
_VALID_BARS = frozenset({"front", "back"})


@dataclass(frozen=True)
class RotationActionSlotRequirement:
    """Explicit bars on which one named skill or ultimate is actually slotted."""

    action_name: str
    allowed_bars: tuple[str, ...]
    action_kind: RotationActionKind = RotationActionKind.SKILL

    def __post_init__(self) -> None:
        name = str(self.action_name or "").strip()
        if not name:
            raise ValueError("rotation slot requirement needs action_name")
        object.__setattr__(self, "action_name", name)

        try:
            kind = (
                self.action_kind
                if isinstance(self.action_kind, RotationActionKind)
                else RotationActionKind(str(self.action_kind))
            )
        except ValueError as exc:
            raise ValueError(
                f"unsupported rotation slot action kind: {self.action_kind!r}"
            ) from exc
        if kind not in _SUPPORTED_KINDS:
            raise ValueError("rotation slot requirements support skill or ultimate actions")
        object.__setattr__(self, "action_kind", kind)

        bars: list[str] = []
        for raw in self.allowed_bars:
            bar = str(raw or "").strip().casefold()
            if bar not in _VALID_BARS:
                raise ValueError("rotation slot allowed bars must be front or back")
            if bar not in bars:
                bars.append(bar)
        if not bars:
            raise ValueError("rotation slot requirement needs at least one allowed bar")
        object.__setattr__(self, "allowed_bars", tuple(bars))


@dataclass(frozen=True)
class RotationActionSlotViolation:
    requirement: RotationActionSlotRequirement
    time_seconds: float
    scheduled_bar: str | None
    scheduled_kind: RotationActionKind

    @property
    def reason(self) -> str:
        if self.scheduled_kind is not self.requirement.action_kind:
            return "scheduled action kind does not match the saved-build slot kind"
        if self.scheduled_bar is None:
            return "scheduled action has no explicit bar"
        return "action is not slotted on the scheduled bar"


@dataclass(frozen=True)
class RotationActionSlotAssessment:
    violations: tuple[RotationActionSlotViolation, ...]

    @property
    def legal(self) -> bool:
        return not self.violations


class RotationActionSlotAssessor:
    """Audit final-plan skill/ultimate casts against explicit slotted-bar evidence.

    The assessor knows nothing about classes, roles, weapons, or encounter strategy.
    Callers supply exact saved-build slot ownership. A known saved-build action must
    keep both its structural action kind (skill vs ultimate) and an explicit bar on
    which that action is actually slotted. Names with no supplied slot evidence are
    deliberately ignored rather than guessed.
    """

    def assess(
        self,
        plan: RotationPlan,
        requirements: tuple[RotationActionSlotRequirement, ...],
    ) -> RotationActionSlotAssessment:
        requirement_by_key: dict[
            tuple[RotationActionKind, str], RotationActionSlotRequirement
        ] = {}
        requirements_by_name: dict[str, list[RotationActionSlotRequirement]] = {}
        for requirement in requirements:
            key = (requirement.action_kind, requirement.action_name.casefold())
            if key in requirement_by_key:
                raise ValueError(
                    "duplicate rotation slot requirement for "
                    f"{requirement.action_name!r}"
                )
            requirement_by_key[key] = requirement
            requirements_by_name.setdefault(requirement.action_name.casefold(), []).append(
                requirement
            )

        violations: list[RotationActionSlotViolation] = []
        for action in plan.actions:
            if action.kind not in _SUPPORTED_KINDS or not action.name:
                continue

            normalized_name = str(action.name).casefold()
            requirement = requirement_by_key.get((action.kind, normalized_name))
            if requirement is None:
                name_matches = requirements_by_name.get(normalized_name, ())
                if len(name_matches) == 1:
                    expected = name_matches[0]
                    violations.append(
                        RotationActionSlotViolation(
                            requirement=expected,
                            time_seconds=float(action.time_seconds),
                            scheduled_bar=action.bar,
                            scheduled_kind=action.kind,
                        )
                    )
                continue

            if action.bar not in requirement.allowed_bars:
                violations.append(
                    RotationActionSlotViolation(
                        requirement=requirement,
                        time_seconds=float(action.time_seconds),
                        scheduled_bar=action.bar,
                        scheduled_kind=action.kind,
                    )
                )

        return RotationActionSlotAssessment(tuple(violations))


__all__ = [
    "RotationActionSlotAssessment",
    "RotationActionSlotAssessor",
    "RotationActionSlotRequirement",
    "RotationActionSlotViolation",
]
