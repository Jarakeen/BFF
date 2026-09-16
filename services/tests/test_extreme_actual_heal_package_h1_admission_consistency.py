from __future__ import annotations

from minmax.gear_sets import GearSet, GearSetBonus
from services.extreme_actual_heal_double_five_package_service import (
    ExtremeActualHealDoubleFivePackageService,
)
from services.extreme_actual_heal_gear_set_candidate_service import (
    ExtremeActualHealGearSetCandidateService,
)
from services.extreme_actual_heal_monster_package_service import (
    ExtremeActualHealMonsterPackageService,
)
from services.extreme_actual_heal_mythic_package_service import (
    ExtremeActualHealMythicPackageService,
)
from services.extreme_actual_heal_non_ring_mythic_package_service import (
    ExtremeActualHealNonRingMythicPackageService,
)


class _Repo:
    def __init__(self) -> None:
        self.sets = (GearSet(1, "Light Speaker", "Test", 5),)
        self.bonuses = {
            1: (
                GearSetBonus(
                    1,
                    1,
                    5,
                    "(5 items) Adds 600 Weapon and Spell Damage to your Restoration Staff abilities.",
                ),
            )
        }

    def list_sets(self):
        return self.sets

    def get_set(self, name):
        return next((row for row in self.sets if row.name == name), None)

    def get_set_by_id(self, set_id):
        return next((row for row in self.sets if row.id == int(set_id)), None)

    def get_bonuses(self, set_id):
        return list(self.bonuses.get(int(set_id), ()))


class _Monster(ExtremeActualHealMonsterPackageService):
    def _ordinary_body_legal(self, set_id, raw_category):
        return True


class _DoubleFive(ExtremeActualHealDoubleFivePackageService):
    def _body_five_legal(self, set_id, raw_category):
        return True

    def _head_shoulders_jewelry_legal(self, set_id, raw_category):
        return True


class _RingMythic(ExtremeActualHealMythicPackageService):
    def _primary_legal(self, set_id, raw_category):
        return True


class _SlotMythic(ExtremeActualHealNonRingMythicPackageService):
    def _ordinary(self, set_id, raw_category):
        return True


def _ordinary_candidate_service(repository) -> ExtremeActualHealGearSetCandidateService:
    service = ExtremeActualHealGearSetCandidateService.__new__(
        ExtremeActualHealGearSetCandidateService
    )
    service.repository = repository
    return service


def _package_service(cls):
    repository = _Repo()
    service = cls.__new__(cls)
    service.repository = repository
    service.ordinary_candidates = _ordinary_candidate_service(repository)
    return service


def test_reviewed_conditional_ordinary_set_survives_all_package_admission_paths() -> None:
    ordinary = _ordinary_candidate_service(_Repo())
    assert ordinary.candidate_set_names(per_objective=None) == ("Light Speaker",)

    monster = _package_service(_Monster)
    assert monster._reviewed_names(monster=False, per_objective=20) == ("Light Speaker",)

    double_five = _package_service(_DoubleFive)
    assert double_five._reviewed_names(
        secondary_shape=False,
        per_objective=20,
    ) == ("Light Speaker",)
    assert double_five._reviewed_names(
        secondary_shape=True,
        per_objective=20,
    ) == ("Light Speaker",)

    ring_mythic = _package_service(_RingMythic)
    assert ring_mythic._reviewed_names(
        shape="primary",
        per_objective=20,
    ) == ("Light Speaker",)

    slot_mythic = _package_service(_SlotMythic)
    assert slot_mythic._reviewed_ordinary_names(per_objective=20) == ("Light Speaker",)
