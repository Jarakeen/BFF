from __future__ import annotations

"""Materialize one sustained-DPS structural family into canonical build/progression state."""

from dataclasses import dataclass

from minmax.character_progression import CharacterProgression
from models.build_model import PlayerBuild
from services.extreme_heal_class_route_service import ExtremeHealClassRouteService
from services.extreme_sustained_dps_structural_family_adapter_service import (
    ExtremeSustainedDPSStructuralFamilyChoice,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSStructuralMaterialization:
    family_index: int
    build: PlayerBuild
    progression: CharacterProgression
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]

    @property
    def complete(self) -> bool:
        return not self.unresolved


class ExtremeSustainedDPSStructuralMaterializationService:
    """Write structural identity onto ordinary canonical build/progression models."""

    def __init__(self, *, progression_service: object) -> None:
        self.progression_service = progression_service

    def materialize(
        self,
        choice: ExtremeSustainedDPSStructuralFamilyChoice,
    ) -> ExtremeSustainedDPSStructuralMaterialization:
        candidate = choice.candidate
        base = PlayerBuild(
            Name="Extreme Sustained DPS Candidate",
            BuildName=f"Extreme Sustained DPS Structural {choice.structural_family_index}",
            Race=candidate.race,
            EsoClass=candidate.class_route.base_class.value,
            Role="DPS",
        )
        build = ExtremeHealClassRouteService.materialize_build(
            base,
            candidate.class_route,
        )
        build.Race = candidate.race
        build.AttributeHealth = int(candidate.attributes.health)
        build.AttributeMagicka = int(candidate.attributes.magicka)
        build.AttributeStamina = int(candidate.attributes.stamina)

        progression = CharacterProgression(
            attributes=candidate.attributes,
            passive_ranks={},
            passive_cp_points={},
        )
        progression = self.progression_service.normalize(
            progression,
            candidate.class_route,
        )

        unresolved = list(build.validate())
        if progression.attributes != candidate.attributes:
            unresolved.append(
                "Structural progression normalization changed the selected attribute allocation"
            )

        selected_lines = tuple(candidate.class_route.equipped_skill_lines)
        actual_lines = tuple(build.ClassSkillLines)
        if actual_lines != selected_lines:
            unresolved.append(
                "Structural build materialization did not preserve the selected class-route skill lines"
            )

        return ExtremeSustainedDPSStructuralMaterialization(
            family_index=int(choice.structural_family_index),
            build=build,
            progression=progression,
            evidence=(
                f"Structural family index: {choice.structural_family_index}",
                f"Race: {build.Race}",
                f"Base class: {build.EsoClass}",
                "Class route: " + ", ".join(actual_lines),
                (
                    "Attributes: "
                    f"H{build.AttributeHealth}/M{build.AttributeMagicka}/S{build.AttributeStamina}"
                ),
                "Structural active-bar duplicate is intentionally not materialized; rotation search owns starting-bar semantics",
            ),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )


__all__ = [
    "ExtremeSustainedDPSStructuralMaterialization",
    "ExtremeSustainedDPSStructuralMaterializationService",
]
