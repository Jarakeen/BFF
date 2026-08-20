from dataclasses import dataclass

from .build_evaluation import BuildEvaluation
from .evaluation_objective import ObjectiveWeights


@dataclass(frozen=True)
class BuildScore:
    """Scored result for a single evaluated build."""

    damage: float
    healing: float
    survivability: float
    sustain: float
    total: float


def score_build(
    evaluation: BuildEvaluation,
    weights: ObjectiveWeights,
) -> BuildScore:
    """Score a build evaluation using the supplied objective weights."""

    damage = evaluation.total_damage_contribution
    healing = evaluation.total_healing_contribution

    survivability = 0.0
    sustain = 0.0

    total = (
        damage * weights.damage
        + healing * weights.healing
        + survivability * weights.survivability
        + sustain * weights.sustain
    )

    return BuildScore(
        damage=damage,
        healing=healing,
        survivability=survivability,
        sustain=sustain,
        total=total,
    )