from __future__ import annotations

from services.extreme_sustained_dps_finite_axis_action_dominance_service import (
    ExtremeSustainedDPSFiniteAxisActionDominanceService,
    ExtremeSustainedDPSFiniteAxisChoice,
)
from services.rotation_candidate_dd_role_output_service import (
    RotationActionDamageOccurrence,
    RotationActionDamageOccurrenceEvidence,
)


class _Evaluator:
    def __init__(self, rows):
        self.rows = rows

    def evaluate(self, choice):
        row = self.rows[choice]
        return RotationActionDamageOccurrenceEvidence(
            action_time_seconds=row.get("time", 1.0),
            action_sequence=row.get("sequence", 0),
            occurrences=tuple(
                RotationActionDamageOccurrence(
                    time_seconds=1.0 + index * 0.5,
                    sequence=index,
                    damage_value=value,
                    source_name=f"source-{index}",
                )
                for index, value in enumerate(row.get("damage", ()))
            ),
            unresolved=tuple(row.get("unresolved", ())),
        )


def test_complete_finite_cp_axis_promotes_coverage_and_numeric_ceiling() -> None:
    result = ExtremeSustainedDPSFiniteAxisActionDominanceService.evaluate(
        candidate_key="branch:cp",
        axes=("champion_points",),
        choices=(
            ExtremeSustainedDPSFiniteAxisChoice("cp:a", "a"),
            ExtremeSustainedDPSFiniteAxisChoice("cp:b", "b"),
        ),
        denominator_proven=True,
        evaluator=_Evaluator(
            {
                "a": {"damage": (100.0, 20.0)},
                "b": {"damage": (150.0,)},
            }
        ),
        source="finite CP action search",
    )

    assert result.axis_coverage.dominated_axes == ("champion_points",)
    assert result.action_ceiling.complete is True
    assert result.upper_bound_damage == 150.0
    assert result.winning_choice_id == "cp:b"


def test_complete_joint_axes_promote_joint_coverage() -> None:
    result = ExtremeSustainedDPSFiniteAxisActionDominanceService.evaluate(
        candidate_key="branch:progression",
        axes=("champion_points", "passive_ranks"),
        choices=(
            ExtremeSustainedDPSFiniteAxisChoice("p:a", "a"),
            ExtremeSustainedDPSFiniteAxisChoice("p:b", "b"),
        ),
        denominator_proven=True,
        evaluator=_Evaluator(
            {
                "a": {"damage": (100.0,)},
                "b": {"damage": (120.0,)},
            }
        ),
        source="finite progression action search",
    )

    assert result.axis_coverage.dominated_axes == (
        "champion_points",
        "passive_ranks",
    )
    assert result.action_ceiling.upper_bound_damage == 120.0


def test_unresolved_choice_blocks_all_numeric_and_axis_promotion() -> None:
    result = ExtremeSustainedDPSFiniteAxisActionDominanceService.evaluate(
        candidate_key="branch:passive",
        axes=("passive_ranks",),
        choices=(
            ExtremeSustainedDPSFiniteAxisChoice("a", "a"),
            ExtremeSustainedDPSFiniteAxisChoice("b", "b"),
        ),
        denominator_proven=True,
        evaluator=_Evaluator(
            {
                "a": {"damage": (100.0,)},
                "b": {"damage": (), "unresolved": ("runtime proc unavailable",)},
            }
        ),
        source="finite passive action search",
    )

    assert result.axis_coverage.dominated_axes == ()
    assert result.action_ceiling.complete is False
    assert result.upper_bound_damage is None
    assert any("runtime proc unavailable" in row for row in result.unresolved)


def test_coordinate_drift_blocks_promotion() -> None:
    result = ExtremeSustainedDPSFiniteAxisActionDominanceService.evaluate(
        candidate_key="branch:gear",
        axes=("named_gear_realization",),
        choices=(
            ExtremeSustainedDPSFiniteAxisChoice("a", "a"),
            ExtremeSustainedDPSFiniteAxisChoice("b", "b"),
        ),
        denominator_proven=True,
        evaluator=_Evaluator(
            {
                "a": {"damage": (100.0,), "time": 1.0},
                "b": {"damage": (110.0,), "time": 2.0},
            }
        ),
        source="finite gear action search",
    )

    assert result.action_ceiling.complete is False
    assert any("coordinate drifted" in row for row in result.unresolved)


def test_unproven_denominator_blocks_promotion_even_when_choices_resolve() -> None:
    result = ExtremeSustainedDPSFiniteAxisActionDominanceService.evaluate(
        candidate_key="branch:open",
        axes=("champion_points",),
        choices=(ExtremeSustainedDPSFiniteAxisChoice("a", "a"),),
        denominator_proven=False,
        evaluator=_Evaluator({"a": {"damage": (100.0,)}}),
        source="incomplete search",
    )

    assert result.axis_coverage.dominated_axes == ()
    assert result.action_ceiling.complete is False
    assert any("not proven complete" in row for row in result.unresolved)


def test_unknown_axis_is_rejected() -> None:
    result = ExtremeSustainedDPSFiniteAxisActionDominanceService.evaluate(
        candidate_key="branch:bad",
        axes=("champion_points", "moon_phase"),
        choices=(ExtremeSustainedDPSFiniteAxisChoice("a", "a"),),
        denominator_proven=True,
        evaluator=_Evaluator({"a": {"damage": (100.0,)}}),
        source="bad search",
    )

    assert result.action_ceiling.complete is False
    assert any("Unknown sustained-DPS mutation axis" in row for row in result.unresolved)
