from types import SimpleNamespace

from minmax.champion_point_static_repository import (
    CHAMPION_SKILL_TYPE_NORMAL,
    CHAMPION_SKILL_TYPE_STAT_POOL_SLOTTABLE,
    ChampionPointRecord,
)
from minmax.character_progression import AttributeAllocation, CharacterProgression
from minmax.effects import Effect, EffectOperation, EffectUnit
from minmax.stat_ids import StatId
from models.build_model import ChampionPointEntry, PlayerBuild
from services.extreme_resource_champion_point_state_service import (
    ExtremeResourceChampionPointStateService,
)


def _record(name: str, *, slottable: bool, max_points: int = 50) -> ChampionPointRecord:
    return ChampionPointRecord(
        name=name,
        skill_type=(
            CHAMPION_SKILL_TYPE_STAT_POOL_SLOTTABLE
            if slottable
            else CHAMPION_SKILL_TYPE_NORMAL
        ),
        max_points=max_points,
        jump_points=(),
        description="fixture",
    )


class _Repository:
    def __init__(self, records, effects):
        self.records = tuple(records)
        self.effects = dict(effects)

    def non_slottable_records(self):
        return tuple(row for row in self.records if row.is_non_slottable)

    def slottable_records(self):
        return tuple(row for row in self.records if row.is_slottable)

    def resolve(self, name, points):
        return self.effects[name], []


class _Audit:
    def __init__(self, complete=True):
        self.complete = complete

    def build(self, objective_key):
        return SimpleNamespace(
            mechanic_complete=self.complete,
            denominator_proven=self.complete,
            unresolved=() if self.complete else ("unresolved CP",),
        )


def _effect(name: str, stat: StatId, value: float) -> Effect:
    return Effect(
        source=f"Champion Point: {name}",
        stat=stat,
        operation=EffectOperation.ADD,
        value=value,
        unit=EffectUnit.FLAT,
    )


def test_state_selects_relevant_non_slottable_and_slottable_resource_cp():
    passive = _record("Hero's Vigor", slottable=False, max_points=20)
    slotted = _record("Boundless Vitality", slottable=True)
    irrelevant = _record("Arcane Supremacy", slottable=True)
    repo = _Repository(
        (passive, slotted, irrelevant),
        {
            "Hero's Vigor": [_effect("Hero's Vigor", StatId.MAX_HEALTH, 560.0)],
            "Boundless Vitality": [_effect("Boundless Vitality", StatId.MAX_HEALTH, 1400.0)],
            "Arcane Supremacy": [_effect("Arcane Supremacy", StatId.MAX_MAGICKA, 1300.0)],
        },
    )
    state = ExtremeResourceChampionPointStateService(
        repository=repo,
        audit_service=_Audit(),
    ).build("max_health")

    assert state.non_slottable_allocations == (("Hero's Vigor", 20, 560.0),)
    assert state.slottable_allocations == (("Boundless Vitality", 50, 1400.0),)
    assert state.reviewed_delta == 1960.0
    assert state.denominator_proven is True
    assert state.unresolved == ()


def test_state_materializes_progression_and_build_without_duplicating_selected_cp():
    state = SimpleNamespace(
        non_slottable_allocations=(("Eldritch Insight", 20, 520.0),),
        slottable_allocations=(("Arcane Supremacy", 50, 1300.0),),
    )
    progression = CharacterProgression(
        attributes=AttributeAllocation(magicka=64),
        passive_ranks={},
        passive_cp_points={},
    )
    build = PlayerBuild(
        ChampionPoints=[ChampionPointEntry(Name="Arcane Supremacy", Points="10")]
    )

    progression = ExtremeResourceChampionPointStateService.materialize_progression(
        progression,
        state,
    )
    build = ExtremeResourceChampionPointStateService.materialize_build(build, state)

    assert progression.passive_cp_allocation("Eldritch Insight") == 20
    assert [(entry.Name, entry.Points) for entry in build.ChampionPoints] == [
        ("Arcane Supremacy", "50")
    ]


def test_incomplete_cp_mechanics_fail_closed_without_materializing_candidates():
    record = _record("Mystery", slottable=True)
    repo = _Repository(
        (record,),
        {"Mystery": [_effect("Mystery", StatId.MAX_STAMINA, 1300.0)]},
    )
    state = ExtremeResourceChampionPointStateService(
        repository=repo,
        audit_service=_Audit(complete=False),
    ).build("max_stamina")

    assert state.denominator_proven is False
    assert state.non_slottable_allocations == ()
    assert state.slottable_allocations == ()
    assert state.unresolved == ("unresolved CP",)


def test_state_build_reuses_objective_state_without_rebuilding_audit_or_repository():
    record = _record("Arcane Supremacy", slottable=True)

    class _CountingRepository(_Repository):
        def __init__(self):
            super().__init__(
                (record,),
                {"Arcane Supremacy": [_effect("Arcane Supremacy", StatId.MAX_MAGICKA, 1300.0)]},
            )
            self.resolve_calls = 0

        def resolve(self, name, points):
            self.resolve_calls += 1
            return super().resolve(name, points)

    class _CountingAudit(_Audit):
        def __init__(self):
            super().__init__(complete=True)
            self.calls = 0

        def build(self, objective_key):
            self.calls += 1
            return super().build(objective_key)

    repo = _CountingRepository()
    audit = _CountingAudit()
    service = ExtremeResourceChampionPointStateService(
        repository=repo,
        audit_service=audit,
    )

    first = service.build("max_magicka")
    second = service.build("MAX_MAGICKA")

    assert second is first
    assert first.slottable_allocations == (("Arcane Supremacy", 50, 1300.0),)
    assert audit.calls == 1
    assert repo.resolve_calls == 1


def test_production_state_services_share_repository_per_database(tmp_path):
    database = tmp_path / "eso.db"
    first = ExtremeResourceChampionPointStateService(database)
    second = ExtremeResourceChampionPointStateService(database)
    other = ExtremeResourceChampionPointStateService(tmp_path / "other.db")

    assert first.repository is second.repository
    assert first.repository is not other.repository
