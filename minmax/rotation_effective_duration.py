from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class RotationEffectiveDurationOverride:
    """Already-resolved build-specific duration evidence for one rotation skill.

    The Rotation Engine must consume the duration that is true for the selected
    canonical build, not blindly reuse a naked tooltip/base duration when gear,
    passives, armor bonuses, or another verified rule changes it.

    This contract intentionally does *not* calculate those ESO mechanics. The
    authoritative build/effect layer must resolve applicability and final duration
    first, then supply that result here with provenance. That keeps Phase 13 from
    growing a second hard-coded set/passive rules dictionary.
    """

    skill_name: str
    duration_seconds: float
    source: str
    bar: str | None = None

    def __post_init__(self) -> None:
        skill = str(self.skill_name or "").strip()
        if not skill:
            raise ValueError("effective rotation duration needs skill_name")
        object.__setattr__(self, "skill_name", skill)

        duration = float(self.duration_seconds)
        if not math.isfinite(duration) or duration <= 0.0:
            raise ValueError("effective rotation duration must be finite and positive")
        object.__setattr__(self, "duration_seconds", duration)

        source = str(self.source or "").strip()
        if not source:
            raise ValueError("effective rotation duration needs provenance source")
        object.__setattr__(self, "source", source)

        if self.bar is not None:
            bar = str(self.bar).strip().casefold()
            if bar not in {"front", "back"}:
                raise ValueError("effective rotation duration bar must be front or back")
            object.__setattr__(self, "bar", bar)

    @property
    def key(self) -> tuple[str, str | None]:
        return (self.skill_name.casefold(), self.bar)


def index_effective_duration_overrides(
    overrides: tuple[RotationEffectiveDurationOverride, ...],
) -> dict[tuple[str, str | None], RotationEffectiveDurationOverride]:
    """Validate and index explicit effective-duration evidence.

    Exact bar-scoped evidence may coexist with an unscoped fallback for the same
    skill. Duplicate evidence for the same exact scope is rejected rather than
    silently choosing whichever source happened to arrive first.
    """

    indexed: dict[tuple[str, str | None], RotationEffectiveDurationOverride] = {}
    for override in overrides:
        key = override.key
        if key in indexed:
            scope = f" on {override.bar} bar" if override.bar else ""
            raise ValueError(
                "duplicate effective rotation duration for "
                f"{override.skill_name!r}{scope}"
            )
        indexed[key] = override
    return indexed


def select_effective_duration_override(
    indexed: dict[tuple[str, str | None], RotationEffectiveDurationOverride],
    *,
    skill_name: str,
    bar: str | None,
) -> RotationEffectiveDurationOverride | None:
    """Prefer exact bar evidence, then an explicit unscoped fallback."""

    skill_key = str(skill_name or "").strip().casefold()
    exact = indexed.get((skill_key, bar))
    if exact is not None:
        return exact
    return indexed.get((skill_key, None))
