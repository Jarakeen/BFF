from dataclasses import dataclass


@dataclass(frozen=True)
class GroupEvaluation:
    group_damage: float
    support_score: float
    survivability_score: float
    mechanic_score: float