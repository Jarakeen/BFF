from dataclasses import dataclass


@dataclass(frozen=True)
class EvaluationContext:
    """Conditions under which a build is evaluated."""

    fight_duration: float | None = None
    target_count: int = 1
    target_resistance: float | None = None