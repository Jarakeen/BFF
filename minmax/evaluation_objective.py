from dataclasses import dataclass
from enum import Enum


class EvaluationObjective(str, Enum):
    DAMAGE = "damage"
    HEALING = "healing"
    SURVIVABILITY = "survivability"
    SUSTAIN = "sustain"


@dataclass(frozen=True)
class ObjectiveWeights:
    damage: float = 0.0
    healing: float = 0.0
    survivability: float = 0.0
    sustain: float = 0.0

    def __post_init__(self) -> None:
        values = (
            self.damage,
            self.healing,
            self.survivability,
            self.sustain,
        )

        if any(value < 0 for value in values):
            raise ValueError(
                "Objective weights cannot be negative."
            )

    def weight_for(
        self,
        objective: EvaluationObjective,
    ) -> float:
        return {
            EvaluationObjective.DAMAGE: self.damage,
            EvaluationObjective.HEALING: self.healing,
            EvaluationObjective.SURVIVABILITY: self.survivability,
            EvaluationObjective.SUSTAIN: self.sustain,
        }[objective]