from types import SimpleNamespace

from services.extreme_best_named_gear_resource_armor_mundus_food_potion_structural_stat_evaluator import (
    ExtremeNamedGearResourceArmorFiniteAxisEvaluatorFactory,
)
from services.extreme_gear_physical_slot_realization_service import ExtremeWeaponSlotShape
from services.extreme_named_gear_set_realization_service import ExtremeNamedGearSetRealization
from services.extreme_structural_mundus_core_stat_record_service import (
    ExtremeBestMundusStructuralStatEvaluator,
)
from services.extreme_twice_born_mundus_structural_stat_evaluator import (
    ExtremeTwiceBornMundusStructuralStatEvaluator,
)


class _Canonical:
    def __init__(self):
        self.optimizer = SimpleNamespace()
        self.progression_service = SimpleNamespace()


class _Repository:
    pass


def _realization(*, twice_born: bool):
    if twice_born:
        names = ("Twice-Born Star", "Other Set")
        counts = (5, 2)
        ids = (10, 20)
    else:
        names = ("Ordinary Five", "Other Set")
        counts = (5, 2)
        ids = (11, 20)
    return ExtremeNamedGearSetRealization(
        topology_signature="5+2|unused:5",
        set_ids=ids,
        set_names=names,
        counts=counts,
        weapon_shape=ExtremeWeaponSlotShape.NONE,
        assignments=(),
    )


def _factory():
    return ExtremeNamedGearResourceArmorFiniteAxisEvaluatorFactory(
        canonical_evaluator=_Canonical(),
        mundus_repository=_Repository(),
        provisioning_repository=_Repository(),
        potion_repository=_Repository(),
        active_bar_state_service=None,
    )


def test_resource_armor_factory_routes_active_twice_born_to_two_mundus_search():
    scorer = _factory()(
        _realization(twice_born=True),
        SimpleNamespace(objective_key="max_magicka"),
    )

    mundus = scorer.food_evaluator.mundus_evaluator
    assert isinstance(mundus, ExtremeTwiceBornMundusStructuralStatEvaluator)
    assert mundus.second_mundus_setter is not None


def test_resource_armor_factory_keeps_ordinary_gear_on_single_mundus_search():
    scorer = _factory()(
        _realization(twice_born=False),
        SimpleNamespace(objective_key="max_magicka"),
    )

    mundus = scorer.food_evaluator.mundus_evaluator
    assert isinstance(mundus, ExtremeBestMundusStructuralStatEvaluator)
