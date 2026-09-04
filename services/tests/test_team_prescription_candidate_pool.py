import json

import pytest

from minmax.build_candidate import BuildCandidate
from minmax.build_candidate_comparison import (
    BuildCandidateComparison,
    CandidateConstraint,
    ConstraintStatus,
)
from minmax.evaluation_objective import EvaluationObjective
from models.build_model import PlayerBuild
from services.team_prescription import PrescribedRoster, PrescribedRosterAssignment, TeamPrescriptionScope
from services.team_prescription_candidate_pool import (
    PrescribedCandidatePoolInput,
    build_prescribed_candidate_pools,
)


def _roster() -> PrescribedRoster:
    return PrescribedRoster(
        name="Godslayer Prescribed Roster",
        goal="Godslayer",
        scope=TeamPrescriptionScope(),
        assignments=(
            PrescribedRosterAssignment(
                slot_name="Main Tank",
                player_name="Susan",
                source_build_name="Necro Tank",
                prescribed_role="Tank",
            ),
            PrescribedRosterAssignment(
                slot_name="DD 1",
                player_name=None,
                source_build_name=None,
                prescribed_role="DD",
            ),
            PrescribedRosterAssignment(
                slot_name="DD 2",
                player_name=None,
                source_build_name=None,
                prescribed_role="DD",
            ),
        ),
    )


def _comparison(candidate_id: str) -> BuildCandidateComparison:
    build = PlayerBuild(Name=candidate_id, BuildName=f"{candidate_id} Build", Role="DD")
    candidate = BuildCandidate.from_build(
        character_id=f"candidate:{candidate_id}",
        baseline_build_id="baseline",
        candidate_id=candidate_id,
        candidate_build=build,
        changes=(),
        candidate_source="phase13:test-pool",
    )
    return BuildCandidateComparison(
        candidate=candidate,
        objective=EvaluationObjective.DAMAGE,
        baseline_value=100.0,
        candidate_value=120.0,
        constraints=(
            CandidateConstraint(
                name="hard",
                status=ConstraintStatus.PRESERVED,
                explanation="structural test",
            ),
        ),
    )


def test_pool_adapter_groups_only_evaluated_open_slot_candidates() -> None:
    result = build_prescribed_candidate_pools(
        roster=_roster(),
        inputs=(
            PrescribedCandidatePoolInput(
                slot_name="DD 1",
                comparison=_comparison("provider-dd"),
                provider_requirement_ids=("sunspire:provider",),
            ),
        ),
    )

    assert tuple(result.pools) == ("DD 1", "DD 2")
    assert result.pools["DD 1"][0].comparison.candidate.candidate_id == "provider-dd"
    assert result.pools["DD 1"][0].provider_requirement_ids == ("sunspire:provider",)
    assert result.pools["DD 2"] == ()
    assert result.unresolved == (
        "DD 2: no evaluated Phase 12 candidate evidence is available",
    )


def test_pool_adapter_rejects_candidate_for_anchored_slot() -> None:
    with pytest.raises(ValueError, match="cannot replace anchored slot"):
        build_prescribed_candidate_pools(
            roster=_roster(),
            inputs=(
                PrescribedCandidatePoolInput(
                    slot_name="Main Tank",
                    comparison=_comparison("replacement"),
                ),
            ),
        )


def test_pool_adapter_skips_complete_prescribed_build_chair_without_false_unresolved() -> None:
    complete = PlayerBuild(BuildName="Published DD", Role="DD")
    roster = PrescribedRoster(
        name="Published Template Roster",
        goal="Godslayer",
        scope=TeamPrescriptionScope(),
        assignments=(
            PrescribedRosterAssignment(
                slot_name="DD 1",
                player_name=None,
                source_build_name="Published DD",
                prescribed_role="DD",
                prescribed_build_json=json.dumps(complete.to_dict()),
            ),
            PrescribedRosterAssignment(
                slot_name="DD 2",
                player_name=None,
                source_build_name=None,
                prescribed_role="DD",
            ),
        ),
    )

    result = build_prescribed_candidate_pools(roster=roster, inputs=())

    assert tuple(result.pools) == ("DD 2",)
    assert result.unresolved == (
        "DD 2: no evaluated Phase 12 candidate evidence is available",
    )

    with pytest.raises(ValueError, match="cannot replace prescribed build slot"):
        build_prescribed_candidate_pools(
            roster=roster,
            inputs=(
                PrescribedCandidatePoolInput(
                    slot_name="DD 1",
                    comparison=_comparison("late-replacement"),
                ),
            ),
        )


def test_pool_adapter_rejects_unknown_slot_and_duplicate_candidate() -> None:
    with pytest.raises(ValueError, match="unknown roster slot"):
        build_prescribed_candidate_pools(
            roster=_roster(),
            inputs=(
                PrescribedCandidatePoolInput(
                    slot_name="DD 99",
                    comparison=_comparison("ghost"),
                ),
            ),
        )

    duplicate = PrescribedCandidatePoolInput(
        slot_name="DD 1",
        comparison=_comparison("same"),
    )
    with pytest.raises(ValueError, match="Duplicate candidate"):
        build_prescribed_candidate_pools(
            roster=_roster(),
            inputs=(duplicate, duplicate),
        )
