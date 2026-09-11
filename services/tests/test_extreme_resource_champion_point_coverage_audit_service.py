from __future__ import annotations

from minmax.champion_point_static_repository import (
    CHAMPION_SKILL_TYPE_NORMAL,
    CHAMPION_SKILL_TYPE_NORMAL_SLOTTABLE,
    ChampionPointRecord,
)
from minmax.effects import Effect, EffectOperation, EffectUnit
from minmax.stat_ids import StatId
from services.extreme_resource_champion_point_coverage_audit_service import (
    ExtremeResourceChampionPointCoverageAuditService,
)


def _record(name: str, *, slottable: bool = False) -> ChampionPointRecord:
    return ChampionPointRecord(
        name=name,
        skill_type=(
            CHAMPION_SKILL_TYPE_NORMAL_SLOTTABLE
            if slottable
            else CHAMPION_SKILL_TYPE_NORMAL
        ),
        max_points=50,
        jump_points=(),
        description="fixture",
    )


class _Repository:
    def __init__(self, *, non_slottable=(), slottable=(), resolved=None):
        self._non_slottable = tuple(non_slottable)
        self._slottable = tuple(slottable)
        self._resolved = dict(resolved or {})

    def non_slottable_records(self):
        return self._non_slottable

    def slottable_records(self):
        return self._slottable

    def resolve(self, name, points):
        return self._resolved[name]


def _effect(name: str, stat: StatId, value: float) -> Effect:
    return Effect(
        source=f"Champion Point: {name}",
        stat=stat,
        operation=EffectOperation.ADD,
        value=value,
        unit=EffectUnit.FLAT,
    )


def test_audit_separates_non_slottable_and_slottable_resource_stars():
    passive = _record("Passive Health")
    slotted = _record("Slotted Health", slottable=True)
    irrelevant = _record("Magicka Only")
    repo = _Repository(
        non_slottable=(passive, irrelevant),
        slottable=(slotted,),
        resolved={
            "Passive Health": ([_effect("Passive Health", StatId.MAX_HEALTH, 1400.0)], []),
            "Slotted Health": ([_effect("Slotted Health", StatId.MAX_HEALTH, 900.0)], []),
            "Magicka Only": ([_effect("Magicka Only", StatId.MAX_MAGICKA, 1300.0)], []),
        },
    )

    audit = ExtremeResourceChampionPointCoverageAuditService(repository=repo).build("max_health")

    assert audit.non_slottable_reviewed == 2
    assert audit.slottable_reviewed == 1
    assert audit.champion_points_reviewed == 3
    assert audit.non_slottable_relevant == ("Passive Health: +1400",)
    assert audit.slottable_relevant == ("Slotted Health: +900",)
    assert audit.proven_irrelevant == ("Magicka Only",)
    assert audit.unresolved == ()
    assert audit.denominator_proven is True
    assert audit.mechanic_complete is True
    assert audit.slottable_search_required is True
    assert audit.projection_complete is False


def test_audit_closes_when_only_non_slottable_resource_cp_is_relevant():
    passive = _record("Passive Magicka")
    irrelevant = _record("Health Only", slottable=True)
    repo = _Repository(
        non_slottable=(passive,),
        slottable=(irrelevant,),
        resolved={
            "Passive Magicka": ([_effect("Passive Magicka", StatId.MAX_MAGICKA, 1300.0)], []),
            "Health Only": ([_effect("Health Only", StatId.MAX_HEALTH, 900.0)], []),
        },
    )

    audit = ExtremeResourceChampionPointCoverageAuditService(repository=repo).build("max_magicka")

    assert audit.denominator_proven is True
    assert audit.mechanic_complete is True
    assert audit.slottable_search_required is False
    assert audit.projection_complete is True


def test_unmapped_cp_stays_explicit_and_blocks_mechanic_completion():
    mystery = _record("Mystery Star", slottable=True)
    repo = _Repository(
        slottable=(mystery,),
        resolved={
            "Mystery Star": (
                [],
                ["Champion Point is dynamic or not yet stat-mapped: Mystery Star"],
            )
        },
    )

    audit = ExtremeResourceChampionPointCoverageAuditService(repository=repo).build("max_stamina")

    assert audit.denominator_proven is True
    assert audit.mechanic_complete is False
    assert audit.projection_complete is False
    assert audit.unresolved


def test_empty_catalog_does_not_claim_denominator_proof():
    audit = ExtremeResourceChampionPointCoverageAuditService(repository=_Repository()).build("max_health")

    assert audit.champion_points_reviewed == 0
    assert audit.denominator_proven is False
    assert audit.projection_complete is False
