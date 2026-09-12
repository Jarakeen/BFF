from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TeamScheduleSlot:
    """One recurring weekly raid block for a team."""

    Day: str
    StartTime: str
    EndTime: str = ""

    @property
    def display_text(self) -> str:
        day = str(self.Day or "").strip()
        start = str(self.StartTime or "").strip()
        end = str(self.EndTime or "").strip()
        if start and end:
            return f"{day} {start}–{end}".strip()
        if start:
            return f"{day} {start}".strip()
        return day


@dataclass(frozen=True)
class TeamSchedule:
    """Human-entered recurring raid schedule and current team focus.

    ``Slots`` is the canonical representation when different raid days use
    different start/end times. ``RaidDays`` and ``RaidTime`` remain for backward
    compatibility with existing saved teams and older exports.
    """

    TeamName: str
    RaidDays: str = ""
    RaidTime: str = ""
    TimeZone: str = ""
    Slots: tuple[TeamScheduleSlot, ...] = ()
    CurrentFocus: str = ""

    @property
    def effective_slots(self) -> tuple[TeamScheduleSlot, ...]:
        if self.Slots:
            return tuple(self.Slots)
        days = [piece.strip() for piece in str(self.RaidDays or "").split(",") if piece.strip()]
        if not days or not str(self.RaidTime or "").strip():
            return ()
        return tuple(
            TeamScheduleSlot(Day=day, StartTime=str(self.RaidTime).strip())
            for day in days
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.effective_slots or self.TimeZone.strip() or self.CurrentFocus.strip())

    @property
    def display_text(self) -> str:
        # Preserve the historical compact display for legacy schedules that use
        # one shared time across multiple days. ``effective_slots`` is useful for
        # calendar behavior, but it must not make old schedules look like newly
        # configured per-day schedules.
        if not self.Slots:
            parts = [
                value.strip()
                for value in (self.RaidDays, self.RaidTime, self.TimeZone)
                if value and value.strip()
            ]
            return "  ·  ".join(parts) if parts else "Schedule not set"

        schedule_text = "  ·  ".join(
            slot.display_text for slot in self.Slots if slot.display_text
        )
        if self.TimeZone and self.TimeZone.strip():
            return f"{schedule_text}  ·  {self.TimeZone.strip()}"
        return schedule_text or "Schedule not set"
