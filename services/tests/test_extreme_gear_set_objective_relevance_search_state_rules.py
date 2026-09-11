from minmax.gear_sets import GearSetBonus
from services.extreme_gear_search_state_rule_service import ExtremeGearSearchStateRule
from services.extreme_gear_set_bonus_breakpoint_service import (
    ExtremeGearSetBonusBreakpointCatalog,
    ExtremeGearSetBonusBreakpoints,
)
from services.extreme_gear_set_objective_relevance_service import (
    ExtremeGearSetObjectiveRelevance,
    ExtremeGearSetObjectiveRelevanceService,
)
from services.extreme_gear_set_objective_service import (
    ExtremeGearSetObjectiveCandidate,
    ExtremeGearSetObjectiveService,
)


class _Set:
    def __init__(self, set_id: int, name: str):
        self.id = set_id
        self.name = name


class _Repository:
    def __init__(self):
        self.rows = {
            1: _Set(1, "Oakensoul Ring"),
            2: _Set(2, "Torc of the Last Ayleid King"),
            3: _Set(3, "Twice-Born Star"),
        }

    def get_set_by_id(self, set_id):
        return self.rows.get(int(set_id))


def _bonus(set_id: int, piece_count: int, text: str) -> GearSetBonus:
    return GearSetBonus(id=set_id, set_id=set_id, piece_count=piece_count, description=text)


def _breakpoints():
    return ExtremeGearSetBonusBreakpointCatalog(
        sets=(
            ExtremeGearSetBonusBreakpoints(1, "Oakensoul Ring", 1, (1,)),
            ExtremeGearSetBonusBreakpoints(2, "Torc of the Last Ayleid King", 1, (1,)),
            ExtremeGearSetBonusBreakpoints(3, "Twice-Born Star", 5, (5,)),
        )
    )


def test_reviewed_search_state_rules_close_max_resource_relevance_denominator(monkeypatch):
    descriptions = {
        "Oakensoul Ring": _bonus(
            1,
            1,
            "(1 item) While equipped, you are unable to swap between your Primary and Backup Weapon Sets and gain Minor Berserk.",
        ),
        "Torc of the Last Ayleid King": _bonus(
            2,
            1,
            "(1 item) Reduce your damage taken by 15%. Adds 1337 Weapon and Spell Damage. Adds 500 Magicka and Stamina Recovery. Disable all other item set bonuses.",
        ),
        "Twice-Born Star": _bonus(
            3,
            5,
            "(5 items) You can have two Mundus Stone boons at the same time.",
        ),
    }

    def fake_candidate(repo, set_name, objective_key, *, equipped_piece_count=None, resolver=None):
        row = repo.rows[{value.name: key for key, value in repo.rows.items()}[set_name]]
        bonus = descriptions[set_name]
        return ExtremeGearSetObjectiveCandidate(
            set_id=row.id,
            set_name=row.name,
            category="Mythic" if row.id in {1, 2} else "Crafted",
            equipped_piece_count=int(equipped_piece_count),
            objective_key=objective_key,
            reviewed_delta=0.0,
            source_bonuses=(bonus,),
            unresolved=(f"{set_name}: active set bonus is not yet mechanic-mapped",),
        )

    monkeypatch.setattr(ExtremeGearSetObjectiveService, "candidate_for_set", fake_candidate)

    catalog = ExtremeGearSetObjectiveRelevanceService(_Repository()).build(
        "max_magicka",
        _breakpoints(),
    )

    by_name = {row.set_name: row for row in catalog.evidence}
    assert by_name["Oakensoul Ring"].status is ExtremeGearSetObjectiveRelevance.PROVEN_IRRELEVANT
    assert by_name["Oakensoul Ring"].search_state_rule is ExtremeGearSearchStateRule.ONE_BAR_ONLY
    assert by_name["Torc of the Last Ayleid King"].status is ExtremeGearSetObjectiveRelevance.PROVEN_IRRELEVANT
    assert by_name["Torc of the Last Ayleid King"].search_state_rule is ExtremeGearSearchStateRule.SUPPRESSES_OTHER_SET_BONUSES
    assert by_name["Twice-Born Star"].status is ExtremeGearSetObjectiveRelevance.RELEVANT
    assert by_name["Twice-Born Star"].search_state_rule is ExtremeGearSearchStateRule.ALLOWS_TWO_MUNDUS
    assert catalog.unresolved == ()
    assert catalog.denominator_proven is True
    assert catalog.candidate_set_ids == (3,)
