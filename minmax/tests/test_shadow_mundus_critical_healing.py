from __future__ import annotations

from models.build_model import PlayerBuild
from minmax.effects import EffectOperation, EffectUnit
from minmax.gear_stat_inputs import GearCalculationInputs
from minmax.mundus_repository import MundusRepository
from minmax.static_build_inputs import StaticBuildInputResolver
from minmax.stat_ids import StatId


def test_shadow_emits_critical_damage_and_healing_percent_effects(tmp_path):
    repository = MundusRepository(tmp_path / "shadow.db")

    effects, unresolved = repository.get_effects("The Shadow")

    assert unresolved == []
    by_stat = {effect.stat: effect for effect in effects}
    assert set(by_stat) == {StatId.CRITICAL_DAMAGE, StatId.CRITICAL_HEALING}

    for stat in (StatId.CRITICAL_DAMAGE, StatId.CRITICAL_HEALING):
        effect = by_stat[stat]
        assert effect.source == "Mundus: The Shadow"
        assert effect.operation is EffectOperation.ADD_PERCENT
        assert effect.unit is EffectUnit.PERCENT
        assert effect.value == 11.0


def test_shadow_static_build_inputs_keep_critical_healing(tmp_path):
    repository = MundusRepository(tmp_path / "shadow.db")
    resolver = StaticBuildInputResolver(mundus_repository=repository)

    result = resolver.apply(GearCalculationInputs(), PlayerBuild(Mundus="The Shadow"))

    assert result.unresolved == ()
    critical_damage = result.core.critical_damage.additive_after_percent
    critical_healing = result.core.critical_healing.additive_after_percent
    assert [(item.label, item.value) for item in critical_damage] == [("Mundus: The Shadow", 0.11)]
    assert [(item.label, item.value) for item in critical_healing] == [("Mundus: The Shadow", 0.11)]
