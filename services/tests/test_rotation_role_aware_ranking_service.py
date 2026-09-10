from services.rotation_candidate_scorecard_service import RotationCandidateScorecard
from services.rotation_plan_consequence_service import (
    RotationPlanConsequence,
    RotationResourceConsequenceKind,
)
from services.rotation_role_aware_ranking_service import (
    RotationRoleAwareRankingInput,
    RotationRoleAwareRankingService,
)


def _consequence() -> RotationPlanConsequence:
    return RotationPlanConsequence(
        resource_kind=RotationResourceConsequenceKind.NEUTRAL,
        cast_deltas=(),
        cost_deltas=(),
        total_cost_delta=0,
        minimum_resource_delta=0,
        ending_resource_delta=0,
        shortfall_delta=0,
        wait_delta=0,
    )


def _scorecard(*, missing_effects: tuple[str, ...] = (), shortfall: int = 0):
    return RotationCandidateScorecard(
        consequence=_consequence(),
        demand_coverage=(),
        missing_required_effects=missing_effects,
        candidate_shortfall=shortfall,
        inherited_unresolved=(),
        candidate_specific_unresolved=(),
    )


def _candidate(
    candidate_id: str,
    *,
    role: str,
    output: float | None,
    support: float | None,
    sustain: float | None = 1000.0,
    displacement: float | None = 0.0,
    scorecard: RotationCandidateScorecard | None = None,
) -> RotationRoleAwareRankingInput:
    return RotationRoleAwareRankingInput(
        candidate_id=candidate_id,
        scorecard=scorecard or _scorecard(),
        role_key=role,
        role_output_value=output,
        role_output_label="effective damage" if role in {"dd", "dps", "damage_dealer"} else "useful output",
        assigned_support_value=support,
        assigned_support_label="assigned support coverage",
        sustain_margin=sustain,
        primary_role_displacement_seconds=displacement,
    )


def test_hard_mechanic_or_effect_failure_loses_regardless_of_dd_output() -> None:
    ranked = RotationRoleAwareRankingService().rank(
        (
            _candidate(
                "huge-damage-misses-job",
                role="dd",
                output=200_000,
                support=1.0,
                scorecard=_scorecard(missing_effects=("major_brittle",)),
            ),
            _candidate(
                "valid-damage",
                role="dd",
                output=120_000,
                support=1.0,
            ),
        )
    )

    assert [item.candidate_id for item in ranked] == [
        "valid-damage",
        "huge-damage-misses-job",
    ]
    assert ranked[0].tier.value == "eligible"
    assert ranked[1].tier.value == "ineligible"


def test_valid_dd_prefers_effective_damage_not_extra_unassigned_support() -> None:
    ranked = RotationRoleAwareRankingService().rank(
        (
            _candidate("more-healing-ish", role="dd", output=118_000, support=999.0),
            _candidate("more-damage", role="dd", output=125_000, support=1.0),
        )
    )

    assert [item.candidate_id for item in ranked] == ["more-damage", "more-healing-ish"]
    assert "effective damage=125000" in ranked[0].role_reasons[0]
    assert "diagnostic unless" in ranked[0].role_reasons[2]


def test_support_candidate_prioritizes_assigned_support_before_optional_output() -> None:
    ranked = RotationRoleAwareRankingService().rank(
        (
            _candidate("more-output", role="healer", output=5000, support=0.92),
            _candidate("better-support", role="healer", output=1000, support=0.99),
        )
    )

    assert [item.candidate_id for item in ranked] == ["better-support", "more-output"]
    assert "assigned support coverage=0.99" in ranked[0].role_reasons[0]


def test_support_policy_uses_sustain_then_displacement_before_optional_output() -> None:
    ranked = RotationRoleAwareRankingService().rank(
        (
            _candidate(
                "fragile-output",
                role="tank",
                output=9000,
                support=1.0,
                sustain=500.0,
                displacement=0.0,
            ),
            _candidate(
                "sustainable",
                role="tank",
                output=1000,
                support=1.0,
                sustain=2500.0,
                displacement=2.0,
            ),
        )
    )

    assert [item.candidate_id for item in ranked] == ["sustainable", "fragile-output"]


def test_workload_or_sustain_hard_failure_cannot_be_rescued_by_output() -> None:
    ranked = RotationRoleAwareRankingService().rank(
        (
            _candidate(
                "shortfall-dps",
                role="dps",
                output=200_000,
                support=0.0,
                scorecard=_scorecard(shortfall=1),
            ),
            _candidate("executable-dps", role="dps", output=100_000, support=0.0),
        )
    )

    assert [item.candidate_id for item in ranked] == ["executable-dps", "shortfall-dps"]
    assert ranked[1].tier.value == "ineligible"


def test_equal_role_evidence_uses_deterministic_candidate_id_only_at_the_end() -> None:
    ranked = RotationRoleAwareRankingService().rank(
        (
            _candidate("Zulu", role="healer", output=1000, support=1.0),
            _candidate("alpha", role="healer", output=1000, support=1.0),
        )
    )

    assert [item.candidate_id for item in ranked] == ["alpha", "Zulu"]


def test_dd_missing_required_role_output_fails_closed_even_when_scorecard_is_valid() -> None:
    ranked = RotationRoleAwareRankingService().rank(
        (
            _candidate("unknown-output", role="dd", output=None, support=None),
            _candidate("proven-output", role="dd", output=100_000, support=None),
        )
    )

    assert [item.candidate_id for item in ranked] == ["proven-output", "unknown-output"]
    assert ranked[0].tier.value == "eligible"
    assert ranked[1].tier.value == "ineligible"
    assert "role ranking evidence missing: role output" in ranked[1].role_reasons
    assert "assigned support coverage=not supplied" in ranked[0].role_reasons[-1]


def test_dd_diagnostic_support_may_be_unknown_without_blocking_candidate() -> None:
    ranked = RotationRoleAwareRankingService().rank(
        (_candidate("dd", role="dps", output=123_000, support=None),)
    )

    assert ranked[0].tier.value == "eligible"
    assert ranked[0].candidate_id == "dd"


def test_support_missing_assigned_support_evidence_fails_closed() -> None:
    ranked = RotationRoleAwareRankingService().rank(
        (
            _candidate("unknown-support", role="healer", output=2000, support=None),
            _candidate("proven-support", role="healer", output=1000, support=0.95),
        )
    )

    assert [item.candidate_id for item in ranked] == ["proven-support", "unknown-support"]
    assert ranked[1].tier.value == "ineligible"
    assert "role ranking evidence missing: assigned support" in ranked[1].role_reasons


def test_support_optional_output_may_be_unknown_after_support_evidence_is_proven() -> None:
    ranked = RotationRoleAwareRankingService().rank(
        (
            _candidate("unknown-output", role="tank", output=None, support=1.0),
            _candidate("known-output", role="tank", output=1000, support=1.0),
        )
    )

    assert all(item.tier.value == "eligible" for item in ranked)
    assert [item.candidate_id for item in ranked] == ["known-output", "unknown-output"]
    assert "Optional useful output=not supplied" in ranked[1].role_reasons[-1]
