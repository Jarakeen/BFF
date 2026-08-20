from pathlib import Path

import pytest

from services.minmax.effects import EffectKind, EffectOperation
from services.minmax.race_effect_service import RaceEffectService
from services.minmax.race_repository import RaceRepository
from services.minmax.stat_ids import StatId


DB_PATH = Path("data/eso.db")

ALTMER_ID = 1


def service() -> RaceEffectService:
    return RaceEffectService(
        repository=RaceRepository(DB_PATH),
    )


def test_altmer_racial_stats_resolve_to_effects():
    effects = service().resolve_effects(ALTMER_ID)

    assert [
        (effect.stat, effect.value)
        for effect in effects
    ] == [
        (StatId.MAX_MAGICKA, 2000.0),
        (StatId.SPELL_DAMAGE, 258.0),
        (StatId.WEAPON_DAMAGE, 258.0),
    ]


def test_racial_effects_are_stat_additions():
    effects = service().resolve_effects(ALTMER_ID)

    assert all(
        effect.kind == EffectKind.STAT
        for effect in effects
    )

    assert all(
        effect.operation == EffectOperation.ADD
        for effect in effects
    )


def test_racial_effect_sources_identify_race():
    effects = service().resolve_effects(ALTMER_ID)

    assert all(
        effect.source == "Altmer racial bonus"
        for effect in effects
    )


def test_unknown_race_returns_no_effects():
    assert service().resolve_effects(999999) == []


def test_unknown_racial_stat_raises_value_error(monkeypatch):
    from services.minmax.race import RaceStat

    repository = RaceRepository(DB_PATH)
    service_instance = RaceEffectService(repository)

    monkeypatch.setattr(
        repository,
        "get_stats",
        lambda race_id: [
            RaceStat(
                id=999,
                race_id=race_id,
                stat="definitely_not_a_stat",
                value=123,
            )
        ],
    )

    with pytest.raises(ValueError, match="Unknown racial stat"):
        service_instance.resolve_effects(ALTMER_ID)