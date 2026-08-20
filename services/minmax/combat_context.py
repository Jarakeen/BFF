from dataclasses import dataclass, field


@dataclass
class CombatContext:
    """State used when evaluating combat-effect applicability."""

    target: str | None = None
    active_conditions: set[str] = field(default_factory=set)
    elapsed_time: float = 0.0
    fight_duration: float | None = None

    def is_active(self, condition: str) -> bool:
        return condition in self.active_conditions

    def remaining_time(self) -> float | None:
        if self.fight_duration is None:
            return None

        return max(
            0.0,
            self.fight_duration - self.elapsed_time,
        )