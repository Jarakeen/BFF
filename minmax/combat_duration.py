from dataclasses import dataclass


@dataclass(frozen=True)
class DurationResult:
    duration: float
    uptime: float


def calculate_duration(
    *,
    duration: float | None,
    fight_duration: float | None,
) -> DurationResult:
    """Calculate basic duration contribution without proc modeling."""

    if duration is None:
        return DurationResult(
            duration=0.0,
            uptime=1.0,
        )

    if duration <= 0:
        return DurationResult(
            duration=0.0,
            uptime=0.0,
        )

    if fight_duration is None or fight_duration <= 0:
        return DurationResult(
            duration=duration,
            uptime=1.0,
        )

    uptime = min(
        duration / fight_duration,
        1.0,
    )

    return DurationResult(
        duration=duration,
        uptime=uptime,
    )