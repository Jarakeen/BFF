from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math

from minmax.rotation_plan import RotationActionKind


class RotationMode(str, Enum):
    """User-authored rotation behavior understood by Phase 13.

    Phase 13 begins with semi-static schedules. Static and dynamic remain explicit
    vocabulary so the editor can persist intent without pretending those planners
    already exist.
    """

    STATIC = "static"
    SEMI_STATIC = "semi_static"
    DYNAMIC = "dynamic"


@dataclass(frozen=True)
class RotationStep:
    """One authored step in a repeatable rotation definition."""

    kind: RotationActionKind
    name: str | None = None
    bar: str | None = None

    def __post_init__(self) -> None:
        try:
            kind = (
                self.kind
                if isinstance(self.kind, RotationActionKind)
                else RotationActionKind(str(self.kind))
            )
        except ValueError as exc:
            raise ValueError(f"unsupported rotation step kind: {self.kind!r}") from exc
        object.__setattr__(self, "kind", kind)

        normalized_name = str(self.name or "").strip()
        object.__setattr__(self, "name", normalized_name or None)

        if self.bar is not None:
            normalized_bar = str(self.bar).strip().casefold()
            if normalized_bar not in {"front", "back"}:
                raise ValueError("rotation step bar must be 'front' or 'back'")
            object.__setattr__(self, "bar", normalized_bar)

        if kind in {RotationActionKind.SKILL, RotationActionKind.ULTIMATE}:
            if not normalized_name:
                raise ValueError(f"{kind.value} rotation step requires a name")
            if self.bar is None:
                raise ValueError(f"{kind.value} rotation step requires an explicit bar")

        if kind is RotationActionKind.POTION and not normalized_name:
            raise ValueError("potion rotation step requires a name")

        if kind is RotationActionKind.BAR_SWAP and self.bar is None:
            raise ValueError("bar-swap rotation step requires the destination bar")


@dataclass(frozen=True)
class RotationDefinition:
    """Editable Phase 13 intent from which a deterministic schedule is produced.

    This is deliberately separate from ``RotationPlan``. The definition records
    what the user wants repeated; the plan records exactly what was scheduled and
    when. Combat consequences remain outside both contracts.
    """

    character_name: str
    build_name: str
    duration_seconds: float
    steps: tuple[RotationStep, ...]
    mode: RotationMode = RotationMode.SEMI_STATIC
    action_interval_seconds: float = 1.0
    initial_bar: str = "front"
    weave_light_attacks: bool = True
    assumptions: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        character_name = str(self.character_name or "").strip()
        build_name = str(self.build_name or "").strip()
        if not character_name:
            raise ValueError("rotation definition requires a character identity")
        if not build_name:
            raise ValueError("rotation definition requires a build identity")
        object.__setattr__(self, "character_name", character_name)
        object.__setattr__(self, "build_name", build_name)

        duration = float(self.duration_seconds)
        if not math.isfinite(duration) or duration < 0:
            raise ValueError("rotation definition duration must be finite and non-negative")
        object.__setattr__(self, "duration_seconds", duration)

        interval = float(self.action_interval_seconds)
        if not math.isfinite(interval) or interval <= 0:
            raise ValueError("rotation action interval must be finite and greater than zero")
        object.__setattr__(self, "action_interval_seconds", interval)

        try:
            mode = self.mode if isinstance(self.mode, RotationMode) else RotationMode(str(self.mode))
        except ValueError as exc:
            raise ValueError(f"unsupported rotation mode: {self.mode!r}") from exc
        object.__setattr__(self, "mode", mode)

        initial_bar = str(self.initial_bar or "").strip().casefold()
        if initial_bar not in {"front", "back"}:
            raise ValueError("rotation definition initial bar must be 'front' or 'back'")
        object.__setattr__(self, "initial_bar", initial_bar)

        steps = tuple(self.steps)
        if not steps:
            raise ValueError("rotation definition requires at least one step")
        object.__setattr__(self, "steps", steps)

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
