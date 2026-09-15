from __future__ import annotations

from types import SimpleNamespace

from minmax.skill_coefficients import SkillCoefficient
from models.build_model import PlayerBuild
from services.extreme_actual_heal_attribute_projection_service import (
    ExtremeActualHealAttributeProjectionService,
)


class _Coefficients:
    def __init__(self, *coefficients):
        self._coefficients = tuple(coefficients)

    def resolve_entity_id(self, entity_id):
        return SimpleNamespace(
            rank=SimpleNamespace(entity_id=entity_id, coefficients=self._coefficients),
            unresolved=(),
        )


def _coefficient(number: int = 1, coefficient_type: str = "8") -> SkillCoefficient:
    return SkillCoefficient(
        coefficient_number=number,
        type=coefficient_type,
        a=0.1,
        b=1.0,
        c=0.0,
        r=1.0,
    )


def test_type8_h1_attribute_projection_proves_full_simplex_and_keeps_two_endpoints():
    service = ExtremeActualHealAttributeProjectionService(
        coefficient_repository=_Coefficients(_coefficient())
    )
    baseline = PlayerBuild(
        BuildName="Mixed healer",
        AttributeHealth=10,
        AttributeMagicka=44,
        AttributeStamina=10,
    )

    result = service.build_candidates(
        baseline,
        entity_id="combat_prayer",
        character_id="char-1",
        baseline_build_id="build-1",
    )

    assert result.denominator_proven is True
    assert result.source_allocations_reviewed == 2145
    assert result.unresolved == ()
    assert "2,145" in result.search_scope[0]
    assert {
        (
            candidate.candidate_build.AttributeHealth,
            candidate.candidate_build.AttributeMagicka,
            candidate.candidate_build.AttributeStamina,
        )
        for candidate in result.candidates
    } == {(0, 64, 0), (0, 0, 64)}
    assert (
        baseline.AttributeHealth,
        baseline.AttributeMagicka,
        baseline.AttributeStamina,
    ) == (10, 44, 10)


def test_existing_endpoint_is_not_rematerialized():
    service = ExtremeActualHealAttributeProjectionService(
        coefficient_repository=_Coefficients(_coefficient())
    )
    baseline = PlayerBuild(
        BuildName="Magicka endpoint",
        AttributeHealth=0,
        AttributeMagicka=64,
        AttributeStamina=0,
    )

    result = service.build_candidates(
        baseline,
        entity_id="combat_prayer",
        character_id="char-1",
        baseline_build_id="build-1",
    )

    assert result.denominator_proven is True
    assert len(result.candidates) == 1
    only = result.candidates[0].candidate_build
    assert (only.AttributeHealth, only.AttributeMagicka, only.AttributeStamina) == (0, 0, 64)


def test_non_type8_heal_refuses_attribute_projection():
    service = ExtremeActualHealAttributeProjectionService(
        coefficient_repository=_Coefficients(_coefficient(coefficient_type="2"))
    )

    result = service.build_candidates(
        PlayerBuild(BuildName="Unsupported coefficient"),
        entity_id="odd_heal",
        character_id="char-1",
        baseline_build_id="build-1",
    )

    assert result.denominator_proven is False
    assert result.candidates == ()
    assert any("supports only type-8" in item for item in result.unresolved)
