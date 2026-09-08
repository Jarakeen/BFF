from __future__ import annotations

from minmax.gear_sets import GearSet, GearSetBonus
from models.build_model import PlayerBuild
from services.extreme_actual_heal_gear_set_candidate_service import (
    ExtremeActualHealGearSetCandidateService,
)


class _Repo:
    def __init__(self):
        self.sets = (
            GearSet(1, "Healing Power", "Test", 5),
            GearSet(2, "Mystery Power", "Test", 5),
            GearSet(3, "Monster Pair", "Monster", 2),
        )
        self.bonuses = {
            1: (
                GearSetBonus(1, 1, 2, "Adds 129 Weapon and Spell Damage"),
                GearSetBonus(2, 1, 5, "Adds 171 Weapon and Spell Damage"),
            ),
            2: (
                GearSetBonus(3, 2, 2, "Adds 129 Weapon and Spell Damage"),
                GearSetBonus(4, 2, 5, "An unresolved bonus worth an unknown amount."),
            ),
            3: (GearSetBonus(5, 3, 2, "Adds 300 Weapon and Spell Damage"),),
        }

    def list_sets(self):
        return self.sets

    def get_set(self, name):
        return next((row for row in self.sets if row.name == name), None)

    def get_set_by_id(self, set_id):
        return next((row for row in self.sets if row.id == int(set_id)), None)

    def get_bonuses(self, set_id):
        return list(self.bonuses.get(int(set_id), ()))


class _HealthRepo(_Repo):
    def __init__(self):
        super().__init__()
        self.sets = (*self.sets, GearSet(4, "Healthy Power", "Test", 5))
        self.bonuses[4] = (
            GearSetBonus(6, 4, 2, "Adds 1206 Maximum Health"),
            GearSetBonus(7, 4, 5, "Adds 1206 Maximum Health"),
        )


def _service() -> ExtremeActualHealGearSetCandidateService:
    service = ExtremeActualHealGearSetCandidateService.__new__(
        ExtremeActualHealGearSetCandidateService
    )
    service.repository = _Repo()
    return service


def test_candidate_pool_requires_reviewed_complete_five_piece_sets():
    service = _service()

    names = service.candidate_set_names(per_objective=5)

    assert names == ("Healing Power",)
    assert "Mystery Power" not in names
    assert "Monster Pair" not in names


def test_candidate_pool_includes_max_health_only_set_for_health_scaling_heals():
    service = ExtremeActualHealGearSetCandidateService.__new__(
        ExtremeActualHealGearSetCandidateService
    )
    service.repository = _HealthRepo()

    names = service.candidate_set_names(per_objective=5)

    assert "Healthy Power" in names


def test_candidate_materializes_set_on_real_body_slots_without_mutating_baseline():
    service = _service()
    baseline = PlayerBuild(BuildName="Healer")
    for slot in baseline.Armor.values():
        slot["Set"] = "Old Set"

    candidates = service.build_candidates(
        baseline,
        character_id="char-1",
        baseline_build_id="build-1",
    )

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.changes[0].path == "Armor.PrimaryFivePieceSet"
    assert sum(
        1 for slot in candidate.candidate_build.Armor.values()
        if slot["Set"] == "Healing Power"
    ) == 5
    assert all(slot["Set"] == "Old Set" for slot in baseline.Armor.values())


def test_existing_primary_set_is_not_reoffered():
    service = _service()
    baseline = PlayerBuild(BuildName="Healer")
    for slot_name in service.BODY_SLOTS[:5]:
        baseline.Armor[slot_name]["Set"] = "Healing Power"

    candidates = service.build_candidates(
        baseline,
        character_id="char-1",
        baseline_build_id="build-1",
    )

    assert candidates == ()
