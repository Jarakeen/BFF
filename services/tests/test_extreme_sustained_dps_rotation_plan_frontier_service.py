from __future__ import annotations

from types import SimpleNamespace

import pytest

from minmax.character_progression import CharacterProgression
from models.build_model import PlayerBuild
from services.extreme_sustained_dps_generated_candidate_assembly_service import (
    ExtremeSustainedDPSAssembledCandidate,
    ExtremeSustainedDPSGeneratedCandidateCoordinate,
)
from services.extreme_sustained_dps_rotation_plan_frontier_service import (
    ExtremeSustainedDPSRotationPlanFrontierService,
)


class _IdentityRefinement:
    def __init__(self):
        self.calls = []

    def refine(self, plan, **kwargs):
        self.calls.append((plan, kwargs))
        return SimpleNamespace(plan=plan)


def _candidate(front=("A", "B"), back=("C", "D")):
    build = PlayerBuild(
        Name="Generated",
        BuildName="Candidate",
        Role="DD",
    )
    build.FrontBarSkills = [*front, *([""] * (5 - len(front))), ""]
    build.BackBarSkills = [*back, *([""] * (5 - len(back))), ""]
    return ExtremeSustainedDPSAssembledCandidate(
        coordinate=ExtremeSustainedDPSGeneratedCandidateCoordinate(1, 2, 3, 4),
        build=build,
        progression=CharacterProgression(),
        evidence=(),
        unresolved=(),
    )


def _service(refinement=None):
    return ExtremeSustainedDPSRotationPlanFrontierService(
        refinement_service=refinement or _IdentityRefinement(),
    )


def test_rotation_family_counts_order_start_and_weave_axes_lazily() -> None:
    result = _service().frontier(_candidate())

    assert result.denominator_proven is True
    assert result.front_order_count == 2
    assert result.back_order_count == 2
    assert result.starting_route_count == 2
    assert result.weave_state_count == 2
    assert result.candidate_count == 16


def test_rotation_family_first_and_last_coordinates_are_deterministic() -> None:
    service = _service()
    candidate = _candidate()

    first = service.candidate_at(candidate, duration_seconds=10.0, index=0)
    last = service.candidate_at(candidate, duration_seconds=10.0, index=15)

    assert first.front_order == ("A", "B")
    assert first.back_order == ("C", "D")
    assert first.starting_bar == "front"
    assert first.weave_light_attacks is False

    assert last.front_order == ("B", "A")
    assert last.back_order == ("D", "C")
    assert last.starting_bar == "back"
    assert last.weave_light_attacks is True


def test_starting_bar_changes_first_scheduled_skill() -> None:
    service = _service()
    candidate = _candidate()

    front_first = service.candidate_at(candidate, duration_seconds=4.0, index=0)
    back_first = service.candidate_at(candidate, duration_seconds=4.0, index=2)

    first_front_skill = next(
        action for action in front_first.plan.actions if action.kind.value == "skill"
    )
    first_back_skill = next(
        action for action in back_first.plan.actions if action.kind.value == "skill"
    )

    assert first_front_skill.name == "A"
    assert first_front_skill.bar == "front"
    assert first_back_skill.name == "C"
    assert first_back_skill.bar == "back"


def test_one_populated_bar_has_one_starting_route() -> None:
    result = _service().frontier(_candidate(front=("A", "B"), back=()))

    assert result.starting_route_count == 1
    assert result.candidate_count == 2 * 1 * 1 * 2


def test_empty_ordinary_skill_bars_fail_closed() -> None:
    result = _service().frontier(_candidate(front=(), back=()))

    assert result.denominator_proven is False
    assert result.candidate_count == 0
    assert any("at least one ordinary" in row for row in result.unresolved)


def test_invalid_rotation_family_index_fails_closed() -> None:
    service = _service()
    candidate = _candidate()
    count = service.frontier(candidate).candidate_count

    with pytest.raises(IndexError):
        service.candidate_at(candidate, duration_seconds=10.0, index=count)



def test_rotation_family_forwards_explicit_encounter_demands_to_canonical_refiner() -> None:
    refinement = _IdentityRefinement()
    service = _service(refinement)
    priorities = object()
    demands = (object(), object())

    result = service.candidate_at(
        _candidate(),
        duration_seconds=10.0,
        index=0,
        priorities=priorities,
        encounter_demands=demands,
    )

    assert result.mechanic_complete is True
    assert refinement.calls
    _, kwargs = refinement.calls[0]
    assert kwargs["priorities"] is priorities
    assert kwargs["demands"] == demands
    assert any("Encounter demand windows supplied: 2" in row for row in result.evidence)
