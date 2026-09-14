from __future__ import annotations

from minmax.effects import Effect, EffectOperation
from minmax.stat_ids import StatId
from services.extreme_recovery_provisioning_projection_service import (
    ExtremeRecoveryProvisioningProjectionService,
)


class _Repository:
    def __init__(self, rows):
        self.rows = rows

    def list_names(self):
        return tuple(self.rows)

    def resolve(self, name):
        return self.rows[name]


def _effect(name: str, stat: StatId, value: float, operation=EffectOperation.ADD):
    return Effect(source=name, stat=stat, operation=operation, value=value)


def test_projects_best_food_and_drink_for_recovery_objective():
    repository = _Repository(
        {
            "Food A": ([_effect("Food A", StatId.HEALTH_RECOVERY, 100.0)], []),
            "Food B": ([_effect("Food B", StatId.HEALTH_RECOVERY, 200.0)], []),
            "Drink A": ([_effect("Drink A", StatId.HEALTH_RECOVERY, 250.0)], []),
        }
    )

    result = ExtremeRecoveryProvisioningProjectionService.project(
        repository,
        kind_by_name={"food a": "food", "food b": "food", "drink a": "drink"},
        objective_key="health_recovery",
    )

    assert result.comparison_proven is True
    assert result.food is not None and result.food.name == "Food B"
    assert result.food.delta == 200.0
    assert result.drink is not None and result.drink.name == "Drink A"
    assert result.drink.delta == 250.0


def test_ignores_other_recovery_stats():
    repository = _Repository(
        {
            "Food": ([_effect("Food", StatId.MAGICKA_RECOVERY, 999.0)], []),
            "Drink": ([_effect("Drink", StatId.HEALTH_RECOVERY, 100.0)], []),
        }
    )

    result = ExtremeRecoveryProvisioningProjectionService.project(
        repository,
        kind_by_name={"food": "food", "drink": "drink"},
        objective_key="health_recovery",
    )

    assert result.food is None
    assert result.drink is not None and result.drink.delta == 100.0


def test_non_additive_target_effect_fails_closed():
    repository = _Repository(
        {
            "Food": (
                [_effect("Food", StatId.HEALTH_RECOVERY, 15.0, EffectOperation.ADD_PERCENT)],
                [],
            ),
        }
    )

    result = ExtremeRecoveryProvisioningProjectionService.project(
        repository,
        kind_by_name={"food": "food"},
        objective_key="health_recovery",
    )

    assert result.food is None
    assert result.unresolved == (
        "Food: unsupported health_recovery provisioning operation add_percent",
    )


def test_unknown_recovery_objective_fails_closed():
    repository = _Repository({})

    result = ExtremeRecoveryProvisioningProjectionService.project(
        repository,
        kind_by_name={},
        objective_key="ultimate_recovery",
    )

    assert result.candidates == ()
    assert result.unresolved
