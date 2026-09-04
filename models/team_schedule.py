from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TeamSchedule:
    """Human-entered recurring raid schedule for one named team."""

    TeamName: str
    RaidDays: str = ""
    RaidTime: str = ""
    TimeZone: str = ""

    @property
    def is_configured(self) -> bool:
        return bool(self.RaidDays.strip() or self.RaidTime.strip() or self.TimeZone.strip())

    @property
    def display_text(self) -> str:
        parts = [
            value.strip()
            for value in (self.RaidDays, self.RaidTime, self.TimeZone)
            if value and value.strip()
        ]
        return "  ·  ".join(parts) if parts else "Schedule not set"
