from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math

from .rotation_plan import RotationActionKind, RotationPlan
from .ultimate_resource_timeline import UltimateGenerationEvent


class HeroismTier(str, Enum):
    MINOR = "minor"
    MAJOR = "major"


_HEROISM_TICK_SECONDS = 1.5
_HEROISM_GAIN = {
    HeroismTier.MINOR: 1.0,
    HeroismTier.MAJOR: 3.0,
}
_BASE_COMBAT_TICK_SECONDS = 1.0
_BASE_COMBAT_GAIN = 3.0
_BASE_COMBAT_WINDOW_SECONDS = 9.0


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


class CombatAttackUltimateGenerationSource:
    """Derive the canonical base Ultimate buff from successful attack triggers.

    Stored UESP combat evidence states that damaging an enemy with a light or
    heavy attack grants 3 Ultimate per second for 9 seconds. Additional attacks
    refresh that one generation window; they do not create stacked copies.

    ``events_from_plan`` is deliberately opt-in because a scheduled attack is not
    itself proof that it damaged a target. The caller must explicitly assert that
    scheduled light/heavy attacks should be treated as successful combat triggers.
    """

    def events_from_plan(
        self,
        *,
        plan: RotationPlan,
        assume_scheduled_attacks_damage: bool,
    ) -> tuple[UltimateGenerationEvent, ...]:
        if not assume_scheduled_attacks_damage:
            return ()
        attack_times = tuple(
            action.time_seconds
            for action in plan.actions
            if action.kind in {
                RotationActionKind.LIGHT_ATTACK,
                RotationActionKind.HEAVY_ATTACK,
            }
        )
        return self.events(
            attack_times=attack_times,
            duration_seconds=plan.duration_seconds,
        )

    def events(
        self,
        *,
        attack_times: tuple[float, ...],
        duration_seconds: float,
    ) -> tuple[UltimateGenerationEvent, ...]:
        duration = float(duration_seconds)
        if not math.isfinite(duration) or duration < 0:
            raise ValueError("base combat Ultimate duration must be finite and non-negative")

        ordered = tuple(sorted(float(value) for value in attack_times))
        if any(not math.isfinite(value) or value < 0 for value in ordered):
            raise ValueError("base combat Ultimate attack times must be finite and non-negative")
        if any(value > duration for value in ordered):
            raise ValueError("base combat Ultimate attack cannot occur after generation duration")
        if not ordered:
            return ()

        generated: list[UltimateGenerationEvent] = []
        active_until = -1.0
        next_tick = None

        for attack_time in ordered:
            if next_tick is None or attack_time > active_until + 1e-9:
                next_tick = attack_time + _BASE_COMBAT_TICK_SECONDS
            active_until = max(active_until, attack_time + _BASE_COMBAT_WINDOW_SECONDS)

            while (
                next_tick is not None
                and next_tick <= active_until + 1e-9
                and next_tick <= duration + 1e-9
            ):
                next_attack = next(
                    (value for value in ordered if value > attack_time and value < next_tick - 1e-9),
                    None,
                )
                if next_attack is not None:
                    break
                generated.append(
                    UltimateGenerationEvent(
                        time_seconds=next_tick,
                        amount=_BASE_COMBAT_GAIN,
                        source="base combat Ultimate generation",
                    )
                )
                next_tick += _BASE_COMBAT_TICK_SECONDS

        deduped: dict[float, UltimateGenerationEvent] = {}
        for event in generated:
            deduped[event.time_seconds] = event
        return tuple(deduped[key] for key in sorted(deduped))
