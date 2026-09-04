from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math


class RotationActionKind(str, Enum):
    """Explicit action categories understood by the Phase 13 schedule contract.

    The contract classifies scheduled intent only. Consequence calculation remains
    owned by the existing combat, sustain, and runtime-effect systems. The same
    schedule contract is intentionally role-neutral so damage, support, tank, and
    healing rotations do not grow competing action models.
    """

    SKILL = "skill"
    LIGHT_ATTACK = "light_attack"
    HEAVY_ATTACK = "heavy_attack"
    ULTIMATE = "ultimate"
    POTION = "potion"
    BAR_SWAP = "bar_swap"
    WAIT = "wait"


@dataclass(frozen=True)
class RotationAction:
    """One deterministic action scheduled by the rotation engine."""

    time_seconds: float
    sequence: int
    kind: RotationActionKind
    name: str | None = None
    bar: str | None = None

    def __post_init__(self) -> None:
        time_seconds = float(self.time_seconds)
        if not math.isfinite(time_seconds) or time_seconds < 0:
            raise ValueError("rotation action time must be finite and non-negative")
        object.__setattr__(self, "time_seconds", time_seconds)

        if self.sequence < 0:
            raise ValueError("rotation action sequence cannot be negative")

        try:
            kind = (
                self.kind
                if isinstance(self.kind, RotationActionKind)
                else RotationActionKind(str(self.kind))
            )
        except ValueError as exc:
            raise ValueError(f"unsupported rotation action kind: {self.kind!r}") from exc
        object.__setattr__(self, "kind", kind)

        if self.bar is not None:
            normalized_bar = str(self.bar).strip().casefold()
            if normalized_bar not in {"front", "back"}:
                raise ValueError("rotation action bar must be 'front' or 'back'")
            object.__setattr__(self, "bar", normalized_bar)

        normalized_name = str(self.name or "").strip()
        requires_name = kind in {
            RotationActionKind.SKILL,
            RotationActionKind.ULTIMATE,
            RotationActionKind.POTION,
        }
        if requires_name and not normalized_name:
            raise ValueError(f"{kind.value} rotation action requires a name")
        if normalized_name:
            object.__setattr__(self, "name", normalized_name)
        else:
            object.__setattr__(self, "name", None)

        if kind is RotationActionKind.BAR_SWAP and self.bar is None:
            raise ValueError("bar-swap rotation action requires the destination bar")


@dataclass(frozen=True)
class RotationPlan:
    """Authoritative immutable Phase 13 schedule for one canonical saved build.

    This object owns only *which supported action happens when*. It intentionally
    contains no ESO damage, healing, resource, proc, duration, or effect formulas.
    Those consequences remain delegated to the existing engines.
    """

    character_name: str
    build_name: str
    duration_seconds: float
    actions: tuple[RotationAction, ...]
    assumptions: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        character_name = str(self.character_name or "").strip()
        build_name = str(self.build_name or "").strip()
        if not character_name:
            raise ValueError("rotation plan requires a character identity")
        if not build_name:
            raise ValueError("rotation plan requires a build identity")
        object.__setattr__(self, "character_name", character_name)
        object.__setattr__(self, "build_name", build_name)

        duration = float(self.duration_seconds)
        if not math.isfinite(duration) or duration < 0:
            raise ValueError("rotation duration must be finite and non-negative")
        object.__setattr__(self, "duration_seconds", duration)

        actions = tuple(self.actions)
        if any(action.time_seconds > duration for action in actions):
            raise ValueError("rotation action cannot occur after plan duration")

        ordered = tuple(
            sorted(
                actions,
                key=lambda action: (
                    action.time_seconds,
                    action.sequence,
                    action.kind.value,
                    action.name or "",
                    action.bar or "",
                ),
            )
        )
        seen_order_keys: set[tuple[float, int]] = set()
        for action in ordered:
            order_key = (float(action.time_seconds), action.sequence)
            if order_key in seen_order_keys:
                raise ValueError(
                    "rotation actions at the same time require distinct sequence values"
                )
            seen_order_keys.add(order_key)
        object.__setattr__(self, "actions", ordered)

        object.__setattr__(
            self,
            "assumptions",
            tuple(str(value).strip() for value in self.assumptions if str(value).strip()),
        )
        object.__setattr__(
            self,
            "unresolved",
            tuple(str(value).strip() for value in self.unresolved if str(value).strip()),
        )
