from types import SimpleNamespace

from minmax.effects import Effect, EffectOperation
from minmax.gear_sets import GearSetBonus
from minmax.stat_ids import StatId
from services.extreme_gear_set_objective_relevance_service import (
    ExtremeGearSetObjectiveRelevance,
)
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveCandidate
from tools.audit_extreme_weapon_damage_named_gear_threshold import (
    _bounded_flat_for_evidence,
    _relaxed_distinct_topology_bound,
)


def test_unmapped_proc_is_added_to_parsed_static_power_line() -> None:
    static = GearSetBonus(
        id=1,
        set_id=10,
        piece_count=2,
        description="Adds 129 Weapon and Spell Damage",
    )
    proc = GearSetBonus(
        id=2,
        set_id=10,
        piece_count=5,
        description=(
            "While your Stamina is below 33%, increase your Weapon and Spell "
            "Damage by 600."
        ),
    )
    candidate = ExtremeGearSetObjectiveCandidate(
        set_id=10,
        set_name="Conditional Power Set",
        category="Trial",
        equipped_piece_count=5,
        objective_key="weapon_damage",
        reviewed_delta=129.0,
        source_bonuses=(static, proc),
        source_effects=(
            Effect(
                operation=EffectOperation.ADD,
                value=129.0,
                source="Conditional Power Set",
                stat=StatId.WEAPON_DAMAGE,
            ),
        ),
        unresolved=("unmapped conditional power proc",),
    )
    row = SimpleNamespace(
        set_name="Conditional Power Set",
        piece_count=5,
        status=ExtremeGearSetObjectiveRelevance.UNRESOLVED,
        candidate=candidate,
    )

    flat, blockers = _bounded_flat_for_evidence(row)

    assert flat == 729.0
    assert blockers == ()


def test_repeated_count_positions_require_distinct_set_identities() -> None:
    topologies = (SimpleNamespace(counts=(1, 1)),)
    by_count = {
        1: [
            (100.0, "Best Set", 1),
            (95.0, "Best Set Duplicate", 1),
            (80.0, "Second Set", 2),
        ]
    }

    score, signature = _relaxed_distinct_topology_bound(by_count, topologies)

    assert score == 180.0
    assert signature == (("Best Set", 1), ("Second Set", 1))


def test_unmapped_percentage_power_remains_an_explicit_blocker() -> None:
    proc = GearSetBonus(
        id=3,
        set_id=11,
        piece_count=5,
        description="Increase your Weapon and Spell Damage by 20% while active.",
    )
    candidate = ExtremeGearSetObjectiveCandidate(
        set_id=11,
        set_name="Percentage Power Set",
        category="Trial",
        equipped_piece_count=5,
        objective_key="weapon_damage",
        reviewed_delta=0.0,
        source_bonuses=(proc,),
        unresolved=("unmapped percentage power proc",),
    )
    row = SimpleNamespace(
        set_name="Percentage Power Set",
        piece_count=5,
        status=ExtremeGearSetObjectiveRelevance.UNRESOLVED,
        candidate=candidate,
    )

    flat, blockers = _bounded_flat_for_evidence(row)

    assert flat == 0.0
    assert len(blockers) == 1
    assert "percentage Weapon Damage set effect" in blockers[0]
