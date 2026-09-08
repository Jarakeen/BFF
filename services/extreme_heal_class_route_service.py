from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
import re

from minmax.character_build.character_class import CLASS_SKILL_LINES, CharacterClass
from minmax.character_build.class_configuration import ClassSkillLineConfiguration


def canonical_class_skill_line_id(value: object) -> str:
    """Normalize imported/display class-line names to canonical snake_case ids."""

    text = str(value or "").strip().casefold().replace("'", "")
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


@dataclass(frozen=True)
class ExtremeHealClassRoute:
    """One structurally legal base-class + equipped-class-line configuration."""

    base_class: CharacterClass
    configuration: ClassSkillLineConfiguration

    @property
    def equipped_skill_lines(self) -> tuple[str, ...]:
        return tuple(self.configuration.effective_skill_lines(self.base_class))

    @property
    def is_subclassed(self) -> bool:
        return not self.configuration.is_pure_class(self.base_class)

    @property
    def foreign_skill_lines(self) -> tuple[str, ...]:
        return tuple(self.configuration.foreign_skill_lines(self.base_class))

    @property
    def class_mastery_allowed(self) -> bool:
        return self.configuration.configuration_allows_class_mastery(self.base_class)


class ExtremeHealClassRouteService:
    """Enumerate legal ESO class-line routes for Extreme heal discovery.

    The legality authority remains ``ClassSkillLineConfiguration``. This service
    does not invent a second subclass rule set; it only enumerates the finite
    configuration space and exposes deterministic route records for the Extreme
    heal catalog/optimizer.
    """

    ALL_CLASS_LINES = tuple(
        sorted(
            {
                skill_line
                for lines in CLASS_SKILL_LINES.values()
                for skill_line in lines
            }
        )
    )

    def routes_for_base_class(
        self,
        base_class: CharacterClass,
    ) -> tuple[ExtremeHealClassRoute, ...]:
        result: list[ExtremeHealClassRoute] = []
        for selected in combinations(self.ALL_CLASS_LINES, 3):
            configuration = ClassSkillLineConfiguration(
                equipped_skill_lines=tuple(selected),
            )
            if configuration.validate(base_class):
                continue
            result.append(
                ExtremeHealClassRoute(
                    base_class=base_class,
                    configuration=configuration,
                )
            )
        return tuple(
            sorted(
                result,
                key=lambda route: (
                    route.is_subclassed,
                    route.equipped_skill_lines,
                ),
            )
        )

    def all_routes(self) -> tuple[ExtremeHealClassRoute, ...]:
        result: list[ExtremeHealClassRoute] = []
        for base_class in CharacterClass:
            result.extend(self.routes_for_base_class(base_class))
        return tuple(
            sorted(
                result,
                key=lambda route: (
                    route.base_class.value,
                    route.is_subclassed,
                    route.equipped_skill_lines,
                ),
            )
        )

    def routes_for_skill_line(
        self,
        skill_line: str,
        *,
        base_class: CharacterClass | None = None,
    ) -> tuple[ExtremeHealClassRoute, ...]:
        line_id = canonical_class_skill_line_id(skill_line)
        if not line_id:
            return ()
        routes = (
            self.routes_for_base_class(base_class)
            if base_class is not None
            else self.all_routes()
        )
        return tuple(
            route
            for route in routes
            if line_id in set(route.equipped_skill_lines)
        )
