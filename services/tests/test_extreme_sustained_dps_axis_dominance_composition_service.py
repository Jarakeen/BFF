from __future__ import annotations

from services.extreme_sustained_dps_axis_dominance_composition_service import (
    CANONICAL_SUSTAINED_DPS_MUTATION_AXES,
    ExtremeSustainedDPSAxisCoverageProof,
    ExtremeSustainedDPSAxisDominanceCompositionService,
)


def test_disjoint_axis_proofs_union_into_complete_dominance_coverage() -> None:
    result = ExtremeSustainedDPSAxisDominanceCompositionService.compose(
        "candidate:a",
        required_axes=("gear_topology", "champion_points", "passive_ranks"),
        proofs=(
            ExtremeSustainedDPSAxisCoverageProof(
                source="gear proof",
                dominated_axes=("gear_topology",),
            ),
            ExtremeSustainedDPSAxisCoverageProof(
                source="progression proof",
                dominated_axes=("champion_points", "passive_ranks"),
            ),
        ),
    )

    assert result.missing_axes == ()
    assert result.proof.complete is True
    assert result.dominated_axes == (
        "gear_topology",
        "champion_points",
        "passive_ranks",
    )


def test_overlapping_proofs_do_not_duplicate_axis_coverage() -> None:
    result = ExtremeSustainedDPSAxisDominanceCompositionService.compose(
        "candidate:b",
        required_axes=("mundus", "food"),
        proofs=(
            ExtremeSustainedDPSAxisCoverageProof(
                source="joint dominance",
                dominated_axes=("mundus", "food"),
            ),
            ExtremeSustainedDPSAxisCoverageProof(
                source="mundus secondary",
                dominated_axes=("mundus",),
            ),
        ),
    )

    assert result.dominated_axes == ("mundus", "food")
    assert result.missing_axes == ()
    assert result.proof.complete is True


def test_missing_axis_keeps_composed_proof_incomplete() -> None:
    result = ExtremeSustainedDPSAxisDominanceCompositionService.compose(
        "candidate:c",
        required_axes=("skill_bars", "rotation_order"),
        proofs=(
            ExtremeSustainedDPSAxisCoverageProof(
                source="bar proof",
                dominated_axes=("skill_bars",),
            ),
        ),
    )

    assert result.missing_axes == ("rotation_order",)
    assert result.proof.complete is False


def test_unknown_coverage_axis_is_unresolved_not_silently_accepted() -> None:
    proof = ExtremeSustainedDPSAxisCoverageProof(
        source="bad proof",
        dominated_axes=("gear_topology", "telepathy"),
    )
    result = ExtremeSustainedDPSAxisDominanceCompositionService.compose(
        "candidate:d",
        required_axes=("gear_topology",),
        proofs=(proof,),
    )

    assert result.proof.complete is False
    assert any("Unknown sustained-DPS mutation axis" in row for row in result.unresolved)


def test_unknown_required_axis_is_unresolved() -> None:
    result = ExtremeSustainedDPSAxisDominanceCompositionService.compose(
        "candidate:e",
        required_axes=("gear_topology", "alchemy_moon_phase"),
        proofs=(
            ExtremeSustainedDPSAxisCoverageProof(
                source="gear proof",
                dominated_axes=("gear_topology",),
            ),
        ),
    )

    assert result.proof.complete is False
    assert any("Unknown required sustained-DPS mutation axis" in row for row in result.unresolved)


def test_canonical_axis_vocabulary_contains_current_generated_search_dimensions() -> None:
    assert {
        "race",
        "class_route",
        "attributes",
        "gear_topology",
        "named_gear_realization",
        "mundus",
        "food",
        "potion_selection",
        "champion_points",
        "passive_ranks",
        "skill_bars",
        "rotation_order",
        "light_attack_weave",
        "ultimate_policy",
        "potion_timing_policy",
        "execute_policy",
        "heavy_attack_policy",
        "runtime_state",
    }.issubset(set(CANONICAL_SUSTAINED_DPS_MUTATION_AXES))



def test_axis_composition_preserves_omitted_scope_from_contributors() -> None:
    result = ExtremeSustainedDPSAxisDominanceCompositionService.compose(
        "candidate:scope",
        required_axes=("ultimate_policy", "potion_timing_policy"),
        proofs=(
            ExtremeSustainedDPSAxisCoverageProof(
                source="anchored family",
                dominated_axes=("ultimate_policy", "potion_timing_policy"),
                omitted_scope=(
                    "continuous potion first-use offset remains open",
                    "deliberate Ultimate delay remains open",
                ),
            ),
        ),
    )

    assert result.proof.complete is True
    assert result.omitted_scope == (
        "continuous potion first-use offset remains open",
        "deliberate Ultimate delay remains open",
    )
