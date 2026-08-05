# services/tamriel_calendar.py  
from __future__ import annotations

from datetime import datetime

# This mirrors OBS_Foundry_v1.4.lua's get_tamriel_date() exactly, so the
# overlay and the archive reports always agree on what day it is in-game.
# Keep any changes to the anchor date/algorithm in sync between both files.

TAMRIEL_MONTHS = [
    "Morning Star", "Sun's Dawn", "First Seed", "Rain's Hand",
    "Second Seed", "Mid Year", "Sun's Height", "Last Seed",
    "Hearthfire", "Frostfall", "Sun's Dusk", "Evening Star",
]

TAMRIEL_WEEKDAYS = [
    "Morndas", "Tirdas", "Middas", "Turdas", "Fredas", "Loredas", "Sundas",
]

_ANCHOR_EARTH = datetime(2026, 7, 23, 12, 0, 0)
_ANCHOR_DAY = 23
_ANCHOR_MONTH = 7  # Sun's Height
_ANCHOR_YEAR = 582


def get_tamriel_date(now: datetime | None = None) -> str:
    now = now or datetime.now()
    days = (now - _ANCHOR_EARTH).days

    day = _ANCHOR_DAY + days
    month = _ANCHOR_MONTH
    year = _ANCHOR_YEAR

    while day > 30:
        day -= 30
        month += 1
        if month > 12:
            month = 1
            year += 1

    while day < 1:
        month -= 1
        if month < 1:
            month = 12
            year -= 1
        day += 30

    weekday = TAMRIEL_WEEKDAYS[((days % 7) + 7) % 7]

    if day % 10 == 1 and day != 11:
        suffix = "st"
    elif day % 10 == 2 and day != 12:
        suffix = "nd"
    elif day % 10 == 3 and day != 13:
        suffix = "rd"
    else:
        suffix = "th"

    return f"{weekday}, {day}{suffix} of {TAMRIEL_MONTHS[month - 1]}, 2E {year}"
