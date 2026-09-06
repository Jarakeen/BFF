from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math

from .ultimate_resource_timeline import UltimateGenerationEvent


class HeroismTier(str, Enum):
    MINOR = "minor"
    MAJOR = "major"


_HEROISM_TICK_SECONDS = 1.5
_HEROISM_GAIN = {
    HeroismTier.MINOR: 1.0,
    HeroismTier.MAJOR: 3.0,
}


@dataclass(frozen=True)
class HeroismWindow:
    """Explicit in-combat Heroism uptime used to derive Ultimate gain ticks.

    The repository source material defines Minor Heroism as 1 Ultimate every
    1.5 seconds and Major Heroism as 3 Ultimate every 1.5 seconds, while in
    combat. This contract requires callers to supply the actual active window;
    it does not infer buff uptime from skills, sets, potions, or encounter state.
    """

    tier: HeroismTier
    start_seconds: float
    end_seconds: float
    in_combat: bool = True
    source: str = "Heroism"

    def __post_init__(self) -> None:
        try:
            tier = self.tier if isinstance(self.tier, HeroismTier) else HeroismTier(str(self.tier).strip().casefold())
        except ValueError as exc:
            raise ValueError(f"unsupported Heroism tier: {self.tier!r}") from exc
        start = float(self.start_seconds)
        end = float(self.end_seconds)
        source = str(self.source or "").strip()
        if not math.isfinite(start) or start < 0:
            raise ValueError("Heroism window start must be finite and non-negative")
        if not math.isfinite(end) or end < start:
            raise ValueError("Heroism window end must be finite and not precede start")
        if not source:
            raise ValueError("Heroism window requires a source")
        object.__setattr__(self, "tier", tier)
        object.__setattr__(self, "start_seconds", start)
        object.__setattr__(self, "end_seconds", end)
        object.__setattr__(self, "source", source)


class HeroismUltimateGenerationSource:
    """Expand explicit Heroism uptime into deterministic Ultimate gain events."""

    def events(
        self,
        *,
        windows: tuple[HeroismWindow, ...],
        duration_seconds: float,
    ) -> tuple[UltimateGenerationEvent, ...]:
        duration = float(duration_seconds)
        if not math.isfinite(duration) or duration < 0:
            raise ValueError("Heroism generation duration must be finite and non-negative")

        generated: list[UltimateGenerationEvent] = []
        for window in windows:
            if window.start_seconds > duration:
                raise ValueError("Heroism window cannot start after generation duration")
            if window.end_seconds > duration:
                raise ValueError("Heroism window cannot end after generation duration")
            if not window.in_combat:
                continue

            tick = window.start_seconds + _HEROISM_TICK_SECONDS
            gain = _HEROISM_GAIN[window.tier]
            tick_index = 1
            while tick <= window.end_seconds + 1e-9:
                generated.append(
                    UltimateGenerationEvent(
                        time_seconds=tick,
                        amount=gain,
                        source=(
                            f"{window.source}: {window.tier.value.title()} Heroism "
                            f"tick {tick_index}"
                        ),
                    )
                )
                tick_index += 1
                tick = window.start_seconds + tick_index * _HEROISM_TICK_SECONDS

        return tuple(
            sorted(
                generated,
                key=lambda event: (event.time_seconds, event.source.casefold()),
            )
        )
