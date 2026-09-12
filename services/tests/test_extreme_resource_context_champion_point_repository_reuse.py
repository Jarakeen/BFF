from types import SimpleNamespace

import services.extreme_named_gear_resource_armor_canonical_stat_evaluator as module
from services.extreme_named_gear_resource_armor_canonical_stat_evaluator import (
    ExtremeNamedGearResourceArmorCanonicalStatEvaluator,
)


def test_extreme_context_factory_reuses_champion_point_state_repository(monkeypatch):
    shared_cp_repository = object()
    captured = {}

    class _Factory:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(module, "ExtremeResourceConditionedPhase5ContextFactory", _Factory)

    optimizer = SimpleNamespace(
        database_path=None,
        race_repository=object(),
        gear_set_repository=object(),
        mundus_repository=object(),
        provisioning_repository=object(),
    )
    evaluator = SimpleNamespace(
        optimizer=optimizer,
        progression_service=object(),
    )
    armor_state = SimpleNamespace(
        objective_key="max_magicka",
    )
    champion_point_state_service = SimpleNamespace(repository=shared_cp_repository)

    result = ExtremeNamedGearResourceArmorCanonicalStatEvaluator(
        evaluator=evaluator,
        armor_state=armor_state,
        champion_point_state_service=champion_point_state_service,
    )

    assert result.context_factory is not None
    assert captured["champion_point_repository"] is shared_cp_repository
    assert captured["race_repository"] is optimizer.race_repository
    assert captured["gear_set_repository"] is optimizer.gear_set_repository
