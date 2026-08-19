from dataclasses import dataclass, field


@dataclass
class CalculationContext:
    conditions: dict[str, bool] = field(default_factory=dict)

    def is_active(self, condition: str) -> bool:
        return self.conditions.get(condition, False)