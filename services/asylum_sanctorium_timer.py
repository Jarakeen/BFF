from __future__ import annotations

"""Pure timing model for Asylum Sanctorium +2 / Perfecta console mode.

The UI deliberately keeps the event inputs manual because FoundryDock runs beside
ESO on console and does not receive authoritative combat events from the game.
The model still makes every countdown deterministic and testable.
"""

from dataclasses import dataclass, field
from enum import Enum


PERFECTA_LIMIT_SECONDS = 15 * 60
MINI_ENRAGE_SECONDS = 3 * 60
MINI_RESPAWN_SECONDS = 60
MINI_ENRAGE_STACK_INTERVAL_SECONDS = 20
MINI_ENRAGE_STACK_CAP = 6
KITE_INTERVAL_SECONDS = 34
PROTECTOR_RESPAWN_SECONDS = 10


class MiniState(str, Enum):
    WAITING = "waiting"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ENRAGED = "enraged"


@dataclass
class MiniTimer:
    name: str
    state: MiniState = MiniState.WAITING
    seconds_in_state: float = 0.0
    activation_count: int = 0

    def mark_active(self) -> None:
        self.state = MiniState.ACTIVE
        self.seconds_in_state = 0.0
        self.activation_count += 1

    def mark_inactive(self) -> None:
        self.state = MiniState.INACTIVE
        self.seconds_in_state = 0.0

    def reset(self) -> None:
        self.state = MiniState.WAITING
        self.seconds_in_state = 0.0
        self.activation_count = 0

    def advance(self, seconds: float) -> None:
        if seconds <= 0 or self.state == MiniState.WAITING:
            return
        self.seconds_in_state += seconds
        if self.state == MiniState.ACTIVE and self.seconds_in_state >= MINI_ENRAGE_SECONDS:
            self.state = MiniState.ENRAGED
        elif self.state == MiniState.INACTIVE and self.seconds_in_state >= MINI_RESPAWN_SECONDS:
            overflow = self.seconds_in_state - MINI_RESPAWN_SECONDS
            self.mark_active()
            self.seconds_in_state = max(0.0, overflow)
            if self.seconds_in_state >= MINI_ENRAGE_SECONDS:
                self.state = MiniState.ENRAGED

    @property
    def enrage_remaining(self) -> float | None:
        if self.state not in {MiniState.ACTIVE, MiniState.ENRAGED}:
            return None
        return max(0.0, MINI_ENRAGE_SECONDS - self.seconds_in_state)

    @property
    def respawn_remaining(self) -> float | None:
        if self.state != MiniState.INACTIVE:
            return None
        return max(0.0, MINI_RESPAWN_SECONDS - self.seconds_in_state)

    @property
    def enrage_stack(self) -> int:
        if self.state != MiniState.ENRAGED:
            return 0
        overdue = max(0.0, self.seconds_in_state - MINI_ENRAGE_SECONDS)
        return min(
            MINI_ENRAGE_STACK_CAP,
            1 + int(overdue // MINI_ENRAGE_STACK_INTERVAL_SECONDS),
        )

    @property
    def callout(self) -> str:
        if self.state == MiniState.WAITING:
            return "Waiting for first activation"
        if self.state == MiniState.INACTIVE:
            remaining = self.respawn_remaining or 0.0
            if remaining <= 15:
                return f"{self.name} back soon"
            return "Respawn countdown"
        if self.state == MiniState.ENRAGED:
            return f"ENRAGED · stack {self.enrage_stack}"
        remaining = self.enrage_remaining or 0.0
        if remaining <= 15:
            return "ENRAGE IMMINENT"
        if remaining <= 30:
            return f"Execute {self.name}"
        if remaining <= 90:
            return "Health check / focus if needed"
        return "Active"


@dataclass
class AsylumPerfectaTimer:
    running: bool = False
    elapsed_seconds: float = 0.0
    deaths: int = 0
    llothis: MiniTimer = field(default_factory=lambda: MiniTimer("Llothis"))
    felms: MiniTimer = field(default_factory=lambda: MiniTimer("Felms"))
    olms_health_percent: int = 100
    seconds_since_kite: float = 0.0
    seconds_since_protector_death: float = 0.0

    def start(self) -> None:
        self.running = True

    def pause(self) -> None:
        self.running = False

    def reset(self) -> None:
        self.running = False
        self.elapsed_seconds = 0.0
        self.deaths = 0
        self.llothis.reset()
        self.felms.reset()
        self.olms_health_percent = 100
        self.seconds_since_kite = 0.0
        self.seconds_since_protector_death = 0.0

    def add_death(self) -> None:
        self.deaths += 1

    def mark_kite(self) -> None:
        self.seconds_since_kite = 0.0

    def mark_protector_death(self) -> None:
        self.seconds_since_protector_death = 0.0

    def advance(self, seconds: float) -> None:
        if not self.running or seconds <= 0:
            return
        self.elapsed_seconds += seconds
        self.seconds_since_kite += seconds
        self.seconds_since_protector_death += seconds
        self.llothis.advance(seconds)
        self.felms.advance(seconds)

    @property
    def perfecta_remaining(self) -> float:
        return max(0.0, PERFECTA_LIMIT_SECONDS - self.elapsed_seconds)

    @property
    def perfecta_status(self) -> str:
        if self.deaths:
            return "FAILED · DEATH"
        if self.elapsed_seconds > PERFECTA_LIMIT_SECONDS:
            return "FAILED · TIME"
        if not self.running and self.elapsed_seconds <= 0:
            return "READY"
        return "ON TRACK"

    @property
    def kite_window_seconds(self) -> float:
        phase = self.seconds_since_kite % KITE_INTERVAL_SECONDS
        return max(0.0, KITE_INTERVAL_SECONDS - phase)

    @property
    def protector_window_seconds(self) -> float:
        return max(0.0, PROTECTOR_RESPAWN_SECONDS - self.seconds_since_protector_death)

    @property
    def next_olms_jump(self) -> int | None:
        # Operational display follows the familiar +2 health thresholds. The
        # first transition is often described around 90/95% in community guides,
        # so the page labels it as "first jump" separately in its source notes.
        for threshold in (90, 75, 50, 25):
            if self.olms_health_percent > threshold:
                return threshold
        return None


def format_clock(seconds: float) -> str:
    total = max(0, int(round(seconds)))
    minutes, secs = divmod(total, 60)
    return f"{minutes:02d}:{secs:02d}"
