from dataclasses import dataclass, field


@dataclass
class CombatContext:
    """State used when evaluating combat-effect applicability."""

    target: str | None = None
    active_conditions: set[str] = field(default_factory=set)
    elapsed_time: float = 0.0

    def is_active(self, condition: str) -> bool:
        return condition in self.active_conditions