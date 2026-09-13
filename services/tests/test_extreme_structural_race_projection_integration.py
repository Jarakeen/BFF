from dataclasses import dataclass

from minmax.character_build.character_class import CharacterClass
from minmax.character_build.class_configuration import ClassSkillLineConfiguration
from minmax.character_progression import AttributeAllocation
from services.extreme_global_search_universe_service import ExtremeGlobalSearchUniverse
from services.extreme_heal_class_route_service import ExtremeHealClassRoute
from services.extreme_resource_race_projection_service import ExtremeResourceRaceProjection
from services.extreme_structural_global_search_service import ExtremeStructuralGlobalSearchService


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
    return ExtremeGlobalSearchUniverse(
        races=("Breton", "Altmer", "Bosmer"),
        class_routes=(_route(),),
        attribute_allocations=(AttributeAllocation(health=0, magicka=64, stamina=0),),
        active_bars=("front", "back"),
        structural_scope=("races", "routes", "attributes", "bars"),
        deferred_dynamic_axes=(),
    )


class _ProjectedScorer:
    def structural_race_projection(self, objective_key, source_races):
        assert objective_key == "max_magicka"
        assert tuple(source_races) == _universe().races
        return ExtremeResourceRaceProjection(
            objective_key="max_magicka",
            source_race_count=3,
            races=("Bosmer", "Altmer"),
            signatures=(0.0, 2000.0),
            denominator_proven=True,
            unresolved=(),
        )

    def __call__(self, _objective_key, candidate):
        values = {"Bosmer": 0.0, "Altmer": 2000.0}
        return values[candidate.race], None, ()


class _IncompleteProjectedScorer(_ProjectedScorer):
    def structural_race_projection(self, objective_key, source_races):
        return ExtremeResourceRaceProjection(
            objective_key="max_magicka",
            source_race_count=3,
            races=("Altmer",),
            signatures=(2000.0,),
            denominator_proven=False,
            unresolved=("incomplete proof",),
        )

    def __call__(self, _objective_key, candidate):
        values = {"Breton": 2000.0, "Altmer": 2000.0, "Bosmer": 0.0}
        return values[candidate.race], None, ()


def test_complete_race_projection_reduces_only_race_axis_and_preserves_structural_proof():
    result = ExtremeStructuralGlobalSearchService(
        _UniverseService(_universe()),
        scorer=_ProjectedScorer(),
    ).search("max_magicka")

    assert result.candidates_scored == 4
    assert result.structural_denominator_proven is True
    assert result.global_denominator_proven is True
    assert result.best is not None
    assert result.best.candidate.race == "Altmer"
    assert any("3 legal races -> 2 exact witnesses" in row for row in result.structural_scope)


def test_incomplete_race_projection_falls_back_to_full_race_enumeration():
    result = ExtremeStructuralGlobalSearchService(
        _UniverseService(_universe()),
        scorer=_IncompleteProjectedScorer(),
    ).search("max_magicka")

    assert result.candidates_scored == 6
    assert result.structural_denominator_proven is True
    assert result.global_denominator_proven is True
