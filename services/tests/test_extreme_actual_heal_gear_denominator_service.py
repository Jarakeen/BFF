from __future__ import annotations

from minmax.gear_sets import GearSet, GearSetBonus
from services.extreme_actual_heal_gear_denominator_service import (
    ExtremeActualHealGearDenominatorService,
    ExtremeActualHealGearDisposition,
)


class _Repo:
    def __init__(self) -> None:
        self.sets = (
            GearSet(1, "Healing Power", "Test", 5),
            GearSet(2, "Mystery Power", "Test", 5),
            GearSet(3, "Monster Pair", "Monster", 2),
            GearSet(4, "Decorative Five", "Test", 5),
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
            4: (
                GearSetBonus(6, 4, 2, "Adds 4% Healing Taken"),
                GearSetBonus(7, 4, 5, "Adds 4% Healing Taken"),
            ),
        }

    def list_sets(self):
        return self.sets

    def get_set(self, name):
        return next((row for row in self.sets if row.name == name), None)

    def get_set_by_id(self, set_id):
        return next((row for row in self.sets if row.id == int(set_id)), None)

    def get_bonuses(self, set_id):
        return list(self.bonuses.get(int(set_id), ()))


def test_denominator_assigns_every_canonical_set_exactly_one_disposition() -> None:
    report = ExtremeActualHealGearDenominatorService(repository=_Repo()).build()

    assert report.denominator_count == 4
    assert report.disposition_total == 4
    assert report.denominator_proven

    by_name = {row.set_name: row for row in report.rows}
    assert by_name["Healing Power"].disposition is ExtremeActualHealGearDisposition.ACCEPTED
    assert by_name["Mystery Power"].disposition is ExtremeActualHealGearDisposition.UNRESOLVED
    assert by_name["Monster Pair"].disposition is ExtremeActualHealGearDisposition.NO_FIVE_PIECE_SHAPE
    assert by_name["Decorative Five"].disposition is ExtremeActualHealGearDisposition.REVIEWED_NONPOSITIVE


def test_denominator_accepted_rows_match_authoritative_candidate_pool() -> None:
    report = ExtremeActualHealGearDenominatorService(repository=_Repo()).build()

    accepted = tuple(
        row.set_name
        for row in report.rows
        if row.disposition is ExtremeActualHealGearDisposition.ACCEPTED
    )

    assert report.accepted_candidate_names == ("Healing Power",)
    assert accepted == ("Healing Power",)
    assert report.candidate_pool_matches_denominator


def test_unresolved_disposition_preserves_objective_and_blocker_evidence() -> None:
    report = ExtremeActualHealGearDenominatorService(repository=_Repo()).build()
    row = next(row for row in report.rows if row.set_name == "Mystery Power")

    assert row.disposition is ExtremeActualHealGearDisposition.UNRESOLVED
    assert row.unresolved_objectives
    assert row.blockers
