from types import SimpleNamespace

from minmax.character_progression import AttributeAllocation
from services.extreme_best_named_gear_resource_armor_mundus_food_potion_structural_stat_evaluator import (
    ExtremeBestNamedGearResourceArmorMundusFoodPotionStructuralStatEvaluator,
    _RESOURCE_CHAMPION_POINT_SCOPE,
)
from services.extreme_structural_global_search_service import (
    ExtremeStructuralGlobalSearchService,
)


class _UniverseService:
    def build(self):
        return SimpleNamespace(
            races=("Breton",),
            class_routes=(
                SimpleNamespace(
                    base_class=SimpleNamespace(value="Warden"),
                    equipped_skill_lines=(),
                ),
            ),
            attribute_allocations=(AttributeAllocation(magicka=64),),
            active_bars=("front",),
            structural_scope=("races", "routes", "attributes", "bars"),
            deferred_dynamic_axes=("Champion Points", "runtime state"),
            structural_denominator_proven=True,
        )


class _ProofOwningScorer:
    def __call__(self, objective_key, candidate):
        return 1.0, {"objective": objective_key}, ()

    def closed_dynamic_axes(self, objective_key):
        assert objective_key == "max_magicka"
        return ("Champion Points",)

    def additional_search_scope(self, objective_key):
        assert objective_key == "max_magicka"
        return ("reviewed CP axis",)


def test_structural_search_accepts_proof_owned_axis_closure_without_knowing_mechanic():
    result = ExtremeStructuralGlobalSearchService(
        _UniverseService(),
        scorer=_ProofOwningScorer(),
    ).search("max_magicka")

    assert "Champion Points" not in result.deferred_dynamic_axes
    assert result.deferred_dynamic_axes == ("runtime state",)
    assert "reviewed CP axis" in result.structural_scope
    assert result.structural_denominator_proven is True


class _ChampionPointState:
    denominator_proven = True
    unresolved = ()


class _Factory:
    def champion_point_state(self, objective_key):
        assert objective_key == "max_health"
        return _ChampionPointState()


def test_resource_scorer_closes_cp_only_when_executable_state_is_proven():
    evaluator = ExtremeBestNamedGearResourceArmorMundusFoodPotionStructuralStatEvaluator(
        gear_realization=SimpleNamespace(),
        armor_catalog=SimpleNamespace(),
        evaluator_factory=_Factory(),
    )

    assert evaluator.closed_dynamic_axes("max_health") == ("Champion Points",)
    assert evaluator.additional_search_scope("max_health") == (
        _RESOURCE_CHAMPION_POINT_SCOPE,
    )


def test_resource_scorer_keeps_cp_open_when_state_is_unresolved():
    class _UnresolvedFactory:
        def champion_point_state(self, objective_key):
            return SimpleNamespace(
                denominator_proven=False,
                unresolved=("CP overflow",),
            )

    evaluator = ExtremeBestNamedGearResourceArmorMundusFoodPotionStructuralStatEvaluator(
        gear_realization=SimpleNamespace(),
        armor_catalog=SimpleNamespace(),
        evaluator_factory=_UnresolvedFactory(),
    )

    assert evaluator.closed_dynamic_axes("max_health") == ()
    assert evaluator.additional_search_scope("max_health") == ()
