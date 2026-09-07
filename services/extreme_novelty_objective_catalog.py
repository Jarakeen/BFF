from __future__ import annotations

"""Named novelty objectives for the Extreme/MOST page.

These recipes define optimization intent and hard equipment/resource constraints
without pretending the underlying mechanic families are already globally
complete. Actual source-family coverage remains governed by the relevant
Extreme coverage and mechanic services.
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
    required_primary_resource: str | None = None
    required_role: str | None = None
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

HEALING_OUTPUT = ExtremeNoveltyMetric(
    objective_key="healing_output",
    label="Healing Output",
    direction=ExtremeObjectiveDirection.MAXIMIZE,
)

HEALING_DONE = ExtremeNoveltyMetric(
    objective_key="healing_done",
    label="Healing Done",
    direction=ExtremeObjectiveDirection.MAXIMIZE,
)

CRITICAL_HEALING = ExtremeNoveltyMetric(
    objective_key="critical_healing",
    label="Critical Healing",
    direction=ExtremeObjectiveDirection.MAXIMIZE,
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

MOST_STAMINA_HEALER = ExtremeNoveltyRecipe(
    key="most_stamina_healer",
    label="MOST Stamina Healer",
    primary=HEALING_OUTPUT,
    secondary=(HEALING_DONE, CRITICAL_HEALING),
    required_primary_resource="stamina",
    required_role="healer",
    note=(
        "Require a genuinely stamina-primary healer route rather than relabeling "
        "a magicka healer. Maximize actual healing output first, then report "
        "Healing Done and Critical Healing as separate supporting metrics. "
        "Sustain is optional for the novelty objective, but skill/equipment "
        "legality and resource-use constraints must still be satisfied."
    ),
)


class ExtremeNoveltyObjectiveCatalog:
    RECIPES = (MOST_SNEAKY, MOST_BASHY, MOST_STAMINA_HEALER)

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
