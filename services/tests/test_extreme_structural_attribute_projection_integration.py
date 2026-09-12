from dataclasses import dataclass

from minmax.character_build.character_class import CharacterClass
from minmax.character_build.class_configuration import ClassSkillLineConfiguration
from minmax.character_progression import AttributeAllocation
from services.extreme_global_search_universe_service import ExtremeGlobalSearchUniverse
from services.extreme_heal_class_route_service import ExtremeHealClassRoute
from services.extreme_resource_attribute_projection_service import (
    ExtremeResourceAttributeProjection,
)
from services.extreme_structural_global_search_service import (
    ExtremeStructuralGlobalSearchService,
)


@dataclass
class _UniverseService:
    universe: ExtremeGlobalSearchUniverse

    def build(self):
        return self.universe


def _route():
    return ExtremeHealClassRoute(
        base_class=CharacterClass.WARDEN,
        configuration=ClassSkillLineConfiguration(
            equipped_skill_lines=("animal_companions", "green_balance", "winters_embrace")
        ),
    )


def _universe():
    allocations = (
        AttributeAllocation(health=64, magicka=0, stamina=0),
        AttributeAllocation(health=0, magicka=64, stamina=0),
    )
    return ExtremeGlobalSearchUniverse(
        races=("Breton",),
        class_routes=(_route(),),
        attribute_allocations=allocations,
        active_bars=("front", "back"),
        structural_scope=("races", "routes", "attributes", "bars"),
        deferred_dynamic_axes=(),
    )


class _ProjectedScorer:
    def structural_attribute_projection(self, objective_key, source_allocations):
        assert objective_key == "max_health"
        assert tuple(source_allocations) == _universe().attribute_allocations
        return ExtremeResourceAttributeProjection(
            objective_key="max_health",
            allocations=(AttributeAllocation(health=64, magicka=0, stamina=0),),
            source_allocations_reviewed=2,
            target_points=64,
            per_point_value=122.0,
            denominator_proven=True,
            scope=("attributes proof-reduced",),
            unresolved=(),
        )

    def __call__(self, _objective_key, candidate):
        return float(candidate.attributes.health), None, ()


class _IncompleteProjectedScorer(_ProjectedScorer):
    def structural_attribute_projection(self, objective_key, source_allocations):
        return ExtremeResourceAttributeProjection(
            objective_key="max_health",
            allocations=(),
            source_allocations_reviewed=1,
            target_points=64,
            per_point_value=122.0,
            denominator_proven=False,
            scope=("must not be used",),
            unresolved=("incomplete proof",),
        )


def test_complete_projection_reduces_only_attribute_axis_and_preserves_structural_proof():
    result = ExtremeStructuralGlobalSearchService(
        _UniverseService(_universe()),
        scorer=_ProjectedScorer(),
    ).search("max_health")

    assert result.candidates_scored == 2
    assert result.structural_denominator_proven is True
    assert result.global_denominator_proven is True
    assert result.best is not None
    assert result.best.candidate.attributes == AttributeAllocation(health=64, magicka=0, stamina=0)
    assert "attributes proof-reduced" in result.structural_scope


def test_incomplete_projection_falls_back_to_full_attribute_enumeration():
    result = ExtremeStructuralGlobalSearchService(
        _UniverseService(_universe()),
        scorer=_IncompleteProjectedScorer(),
    ).search("max_health")

    assert result.candidates_scored == 4
    assert result.structural_denominator_proven is True
    assert result.global_denominator_proven is True
    assert "must not be used" not in result.structural_scope
