from minmax.gear_set_healing_condition_resolver import GearSetHealingConditionResolver
from minmax.gear_sets import GearSetBonus
from minmax.stat_ids import StatId
from models.build_model import PlayerBuild
from services.extreme_actual_heal_gear_precondition_witness_service import (
    BEACON_OF_OBLIVION_NO_PERMANENT_PET_PVE_CONDITION,
    ExtremeActualHealGearPreconditionWitnessService,
)
from services.extreme_actual_heal_gear_set_candidate_service import (
    ExtremeActualHealGearSetCandidateService,
)
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveCandidate


DESCRIPTION = (
    "(5 items) While you have a permanent pet active, gain |cffffff1840|r Health "
    "and |cffffff1980|r Armor.\n\nWhile you do not have a permanent pet active, "
    "increase your Damage Done and Healing Done by |cffffff15|r%. This value is "
    "reduced to |cffffff7|r% while affected by Battle Spirit."
)


def _build(piece_count: int) -> PlayerBuild:
    build = PlayerBuild()
    for slot in ("Head", "Chest", "Legs", "Shoulders", "Hands")[:piece_count]:
        build.Armor[slot]["Set"] = "Beacon of Oblivion"
    return build


def test_beacon_exact_pve_no_pet_branch_maps_to_fifteen_percent_healing_done() -> None:
    effects = GearSetHealingConditionResolver().resolve(
        GearSetBonus(id=1, set_id=1, piece_count=5, description=DESCRIPTION)
    )

    assert len(effects) == 1
    assert effects[0].stat == StatId.HEALING_DONE
    assert effects[0].value == 15.0
    assert effects[0].condition == BEACON_OF_OBLIVION_NO_PERMANENT_PET_PVE_CONDITION


def test_beacon_changed_pvp_reduction_fails_closed() -> None:
    changed = DESCRIPTION.replace("|cffffff7|r%", "|cffffff8|r%")
    effects = GearSetHealingConditionResolver().resolve(
        GearSetBonus(id=1, set_id=1, piece_count=5, description=changed)
    )
    assert effects == []


def test_beacon_requires_five_pieces_for_no_pet_pve_witness() -> None:
    inactive = ExtremeActualHealGearPreconditionWitnessService.resolve(_build(4))
    active = ExtremeActualHealGearPreconditionWitnessService.resolve(_build(5))

    assert BEACON_OF_OBLIVION_NO_PERMANENT_PET_PVE_CONDITION not in inactive.condition_context
    assert BEACON_OF_OBLIVION_NO_PERMANENT_PET_PVE_CONDITION in active.condition_context
    assert any("dismissed or unsummoned" in item for item in active.evidence)
    assert any("outside Battle Spirit" in item for item in active.evidence)


def test_beacon_condition_blocker_is_reviewed_only_for_healing_done() -> None:
    blocker = (
        "Beacon of Oblivion (5): relevant set effect requires condition "
        "beacon_of_oblivion_no_permanent_pet_pve"
    )
    healing_row = ExtremeGearSetObjectiveCandidate(
        set_id=1,
        set_name="Beacon of Oblivion",
        category="Test",
        equipped_piece_count=5,
        objective_key="healing_done",
        reviewed_delta=0.0,
        unresolved=(blocker,),
    )
    health_row = ExtremeGearSetObjectiveCandidate(
        set_id=1,
        set_name="Beacon of Oblivion",
        category="Test",
        equipped_piece_count=5,
        objective_key="max_health",
        reviewed_delta=0.0,
        unresolved=(blocker,),
    )

    healing = ExtremeActualHealGearSetCandidateService._h1_review(healing_row)
    health = ExtremeActualHealGearSetCandidateService._h1_review(health_row)

    assert healing.h1_mechanic_complete is True
    assert healing.h1_positive_modifier_proven is True
    assert healing.ignored_blockers == (blocker,)
    assert healing.remaining_blockers == ()
    assert health.h1_mechanic_complete is False
    assert health.h1_positive_modifier_proven is False
    assert health.remaining_blockers == (blocker,)
