from __future__ import annotations

from minmax.effects import EffectOperation, EffectUnit
from minmax.mundus_repository import MundusRepository
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
