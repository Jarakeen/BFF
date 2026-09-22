from __future__ import annotations

from dataclasses import replace

from minmax.character_build.character_class import CharacterClass
from minmax.character_build.class_configuration import ClassSkillLineConfiguration
from minmax.character_progression import AttributeAllocation
from services.extreme_heal_class_route_service import ExtremeHealClassRoute
from services.extreme_sustained_dps_generated_candidate_service import (
    ExtremeSustainedDPSStructuralCandidate,
)
from services.extreme_sustained_dps_structural_family_adapter_service import (
    ExtremeSustainedDPSStructuralFamilyChoice,
)
from services.extreme_sustained_dps_structural_materialization_service import (
    ExtremeSustainedDPSStructuralMaterializationService,
)


class _Progression:
    def normalize(self, progression, route):
        return replace(
            progression,
            owned_skill_lines=tuple(route.equipped_skill_lines),
        )


def _choice():
    route = ExtremeHealClassRoute(
        base_class=CharacterClass.ARCANIST,
        configuration=ClassSkillLineConfiguration(
            equipped_skill_lines=(
                "herald_of_the_tome",
                "soldier_of_apocrypha",
                "curative_runeforms",
            ),
        ),
    )
    return ExtremeSustainedDPSStructuralFamilyChoice(
        structural_family_index=7,
        candidate=ExtremeSustainedDPSStructuralCandidate(
            structural_index=14,
            race="Khajiit",
            class_route=route,
            attributes=AttributeAllocation(
                health=0,
                magicka=64,
                stamina=0,
            ),
            active_bar="front",
        ),
        source_front_index=14,
        source_back_index=15,
    )


def test_materializes_structural_family_into_build_and_progression() -> None:
    service = ExtremeSustainedDPSStructuralMaterializationService(
        progression_service=_Progression()
    )

    result = service.materialize(_choice())

    assert result.complete is True
    assert result.family_index == 7
    assert result.build.Race == "Khajiit"
    assert result.build.EsoClass == CharacterClass.ARCANIST.value
    assert result.build.AttributeHealth == 0
    assert result.build.AttributeMagicka == 64
    assert result.build.AttributeStamina == 0
    assert tuple(result.build.ClassSkillLines) == (
        "herald_of_the_tome",
        "soldier_of_apocrypha",
        "curative_runeforms",
    )
    assert result.progression.attributes.magicka == 64
    assert tuple(result.progression.owned_skill_lines) == tuple(
        result.build.ClassSkillLines
    )
    assert any(
        "rotation search owns starting-bar semantics" in row
        for row in result.evidence
    )


def test_materialization_does_not_create_an_active_bar_build_field() -> None:
    service = ExtremeSustainedDPSStructuralMaterializationService(
        progression_service=_Progression()
    )

    result = service.materialize(_choice())

    assert "active_bar" not in result.build.to_dict()
