from minmax.champion_point_static_repository import (
    CHAMPION_SKILL_TYPE_STAT_POOL_SLOTTABLE,
    ChampionPointRecord,
    ChampionPointStaticRepository,
)
from minmax.stat_ids import StatId


def _repository_with(record: ChampionPointRecord) -> ChampionPointStaticRepository:
    repository = ChampionPointStaticRepository(":memory:")
    repository._record_cache[record.name] = record
    return repository


def _record(name: str, description: str) -> ChampionPointRecord:
    return ChampionPointRecord(
        name=name,
        skill_type=CHAMPION_SKILL_TYPE_STAT_POOL_SLOTTABLE,
        max_points=50,
        jump_points=(),
        description=description,
    )


def test_arcane_supremacy_inverse_wording_resolves_max_magicka():
    record = _record(
        "Arcane Supremacy",
        "Increases Max Magicka by 26 per stage.",
    )
    effects, unresolved = _repository_with(record).resolve(record.name, 50)

    assert unresolved == []
    assert len(effects) == 1
    assert effects[0].stat is StatId.MAX_MAGICKA
    assert effects[0].value == 1300.0


def test_endless_endurance_inverse_wording_resolves_max_stamina():
    record = _record(
        "Endless Endurance",
        "Increases your Max Stamina by 26 per stage.",
    )
    effects, unresolved = _repository_with(record).resolve(record.name, 50)

    assert unresolved == []
    assert len(effects) == 1
    assert effects[0].stat is StatId.MAX_STAMINA
    assert effects[0].value == 1300.0
