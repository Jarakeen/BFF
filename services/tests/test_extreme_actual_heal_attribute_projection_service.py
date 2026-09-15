from __future__ import annotations

from types import SimpleNamespace

from minmax.skill_coefficients import SkillCoefficient
from minmax.skill_component_classification import SkillEffectKind
from models.build_model import PlayerBuild
from services.extreme_actual_heal_attribute_projection_service import (
    ExtremeActualHealAttributeProjectionService,
)


class _Coefficients:
    def __init__(self, *coefficients):
        self._coefficients = tuple(coefficients)

    def resolve_entity_id(self, entity_id):
        return SimpleNamespace(
            rank=SimpleNamespace(
                entity_id=entity_id,
                skill_rank_id=42,
                coefficients=self._coefficients,
            ),
            unresolved=(),
        )


class _Components:
    def __init__(self, *rows):
        self.rows = tuple(rows)

    def get_for_skill_rank(self, skill_rank_id):
        assert skill_rank_id == 42
        return self.rows


def _component(number: int, kind: SkillEffectKind = SkillEffectKind.HEAL):
    return SimpleNamespace(coefficient_number=number, effect_kind=kind)


def _coefficient(
    number: int = 1,
    coefficient_type: str = "8",
    *,
    a: float = 0.1,
) -> SkillCoefficient:
    return SkillCoefficient(
        coefficient_number=number,
        type=coefficient_type,
        a=a,
        b=1.0,
        c=0.0,
        r=1.0,
    )


def _service(*coefficients, components=None):
    return ExtremeActualHealAttributeProjectionService(
        coefficient_repository=_Coefficients(*coefficients),
        component_repository=_Components(
            *(components or tuple(_component(row.coefficient_number) for row in coefficients))
        ),
    )


def test_type8_h1_attribute_projection_proves_full_simplex_and_keeps_two_endpoints():
    service = _service(_coefficient())
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
    assert "non-negative" in result.search_scope[0]
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
    service = _service(_coefficient())
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
    service = _service(_coefficient(coefficient_type="2"))

    result = service.build_candidates(
        PlayerBuild(BuildName="Unsupported coefficient"),
        entity_id="odd_heal",
        character_id="char-1",
        baseline_build_id="build-1",
    )

    assert result.denominator_proven is False
    assert result.candidates == ()
    assert any("supports only type-8 HEAL coefficients" in item for item in result.unresolved)


def test_negative_heal_resource_slope_refuses_endpoint_dominance():
    service = _service(_coefficient(a=-0.1))

    result = service.build_candidates(
        PlayerBuild(BuildName="Negative heal slope"),
        entity_id="odd_heal",
        character_id="char-1",
        baseline_build_id="build-1",
    )

    assert result.denominator_proven is False
    assert result.candidates == ()
    assert any("negative HEAL resource coefficient" in item for item in result.unresolved)


def test_negative_non_heal_component_does_not_block_heal_attribute_proof():
    service = _service(
        _coefficient(1, a=0.1),
        _coefficient(2, a=-0.5),
        components=(
            _component(1, SkillEffectKind.HEAL),
            _component(2, SkillEffectKind.DAMAGE),
        ),
    )

    result = service.build_candidates(
        PlayerBuild(BuildName="Mixed effect"),
        entity_id="mixed_effect_skill",
        character_id="char-1",
        baseline_build_id="build-1",
    )

    assert result.denominator_proven is True
    assert result.unresolved == ()
