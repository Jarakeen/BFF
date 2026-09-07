from __future__ import annotations

"""Named novelty objectives for the Extreme/MOST page.

These recipes define optimization intent and hard equipment constraints without
pretending the underlying mechanic families are already globally complete.
Actual source-family coverage remains governed by the relevant Extreme coverage
and mechanic services.
"""

from dataclasses import dataclass
from enum import Enum


class ExtremeObjectiveDirection(str, Enum):
    MAXIMIZE = "maximize"
    MINIMIZE = "minimize"


@dataclass(frozen=True)
class ExtremeNoveltyMetric:
    objective_key: str
    label: str
    direction: ExtremeObjectiveDirection


@dataclass(frozen=True)
class ExtremeNoveltyRecipe:
    key: str
    label: str
    primary: ExtremeNoveltyMetric
    secondary: tuple[ExtremeNoveltyMetric, ...] = ()
    required_front_weapon_family: str | None = None
    required_back_weapon_family: str | None = None
    note: str = ""


DETECTION_RADIUS_REDUCTION = ExtremeNoveltyMetric(
    objective_key="detection_radius_reduction",
    label="Detection Radius Reduction",
    direction=ExtremeObjectiveDirection.MAXIMIZE,
)

SNEAK_COST_REDUCTION = ExtremeNoveltyMetric(
    objective_key="sneak_cost_reduction",
    label="Sneak Cost Reduction",
    direction=ExtremeObjectiveDirection.MAXIMIZE,
)

BASH_DAMAGE = ExtremeNoveltyMetric(
    objective_key="bash_damage",
    label="Bash Damage",
    direction=ExtremeObjectiveDirection.MAXIMIZE,
)

BASH_COST = ExtremeNoveltyMetric(
    objective_key="bash_cost",
    label="Bash Cost",
    direction=ExtremeObjectiveDirection.MINIMIZE,
)


MOST_SNEAKY = ExtremeNoveltyRecipe(
    key="most_sneaky",
    label="MOST Sneaky",
    primary=DETECTION_RADIUS_REDUCTION,
    secondary=(SNEAK_COST_REDUCTION,),
    note=(
        "Prioritize the smallest practical detection radius, then the cheapest "
        "Sneak cost. Detection and cost remain separate metrics so the result "
        "can explain tradeoffs instead of collapsing them into an opaque score."
    ),
)

MOST_BASHY = ExtremeNoveltyRecipe(
    key="most_bashy",
    label="MOST Bashy",
    primary=BASH_DAMAGE,
    secondary=(BASH_COST,),
    required_front_weapon_family="one_hand_and_shield",
    required_back_weapon_family="one_hand_and_shield",
    note=(
        "Require sword-and-board legality on both bars. Maximize bash damage and "
        "report the minimum-bash-cost companion result separately because the "
        "two objectives can prefer different equipment and source choices."
    ),
)


class ExtremeNoveltyObjectiveCatalog:
    RECIPES = (MOST_SNEAKY, MOST_BASHY)

    @classmethod
    def all_recipes(cls) -> tuple[ExtremeNoveltyRecipe, ...]:
        return cls.RECIPES

    @classmethod
    def get(cls, key: str) -> ExtremeNoveltyRecipe:
        normalized = str(key or "").strip().casefold()
        for recipe in cls.RECIPES:
            if recipe.key.casefold() == normalized:
                return recipe
        raise KeyError(f"unknown Extreme novelty recipe: {key!r}")
