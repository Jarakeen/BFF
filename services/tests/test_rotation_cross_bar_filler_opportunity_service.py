from types import SimpleNamespace

from minmax.rotation_ability_priority import AbilityPriorityEntry, AbilityPriorityList
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_cross_bar_filler_opportunity_service import (
    RotationCrossBarFillerOpportunityService,
)


def _action(time_seconds, sequence, kind, name=None, bar=None):
    return RotationAction(
        time_seconds=float(time_seconds),
        sequence=int(sequence),
        kind=kind,
        name=name,
        bar=bar,
    )


class _DurationAnalysis:
    def __init__(self, immediate):
        self.immediate = {str(name).casefold() for name in immediate}

    def analyze(self, plan):
        skill = next(action for action in plan.actions if action.kind is RotationActionKind.SKILL)
        if str(skill.name).casefold() in self.immediate:
            return SimpleNamespace(rules=(), unresolved=())
        return SimpleNamespace(
            rules=(),
            unresolved=(f"{skill.name}: duration identity unresolved",),
        )


def _plan():
    return RotationPlan(
        character_name="Rylonia",
        build_name="Corpsebuster DD",
        duration_seconds=12.0,
        actions=(
            _action(0, 1, RotationActionKind.SKILL, "Venom Skull", "front"),
            _action(1, 1, RotationActionKind.SKILL, "Other Spammable", "front"),
            _action(2, 0, RotationActionKind.BAR_SWAP, bar="back"),
            _action(3, 1, RotationActionKind.SKILL, "Stampede", "back"),
            _action(4, 0, RotationActionKind.WAIT, bar="back"),
        ),
    )


def test_back_bar_wait_reports_reviewed_front_bar_immediate_filler() -> None:
    service = RotationCrossBarFillerOpportunityService(
        duration_analysis=_DurationAnalysis({"Venom Skull"}),
    )

    opportunities = service.find(_plan())

    assert len(opportunities) == 1
    item = opportunities[0]
    assert item.wait_time_seconds == 4.0
    assert item.wait_bar == "back"
    assert item.target_bar == "front"
    assert item.filler_skill_name == "Venom Skull"
    assert item.filler_priority is None


def test_explicit_priorities_select_highest_ranked_proven_immediate_filler() -> None:
    service = RotationCrossBarFillerOpportunityService(
        duration_analysis=_DurationAnalysis({"Venom Skull", "Other Spammable"}),
    )
    priorities = AbilityPriorityList(
        character_name="Rylonia",
        build_name="Corpsebuster DD",
        role="DD",
        entries=(
            AbilityPriorityEntry("front", 1, "Venom Skull", 2),
            AbilityPriorityEntry("front", 2, "Other Spammable", 1),
            AbilityPriorityEntry("back", 5, "Stampede", 1),
        ),
    )

    opportunities = service.find(_plan(), priorities=priorities)

    assert len(opportunities) == 1
    assert opportunities[0].filler_skill_name == "Other Spammable"
    assert opportunities[0].filler_priority == 1


def test_unknown_opposite_bar_skill_does_not_become_filler_by_absence_of_rule() -> None:
    service = RotationCrossBarFillerOpportunityService(
        duration_analysis=_DurationAnalysis(set()),
    )

    assert service.find(_plan()) == ()
