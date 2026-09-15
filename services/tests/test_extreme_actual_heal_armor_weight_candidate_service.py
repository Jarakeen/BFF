from __future__ import annotations

from types import SimpleNamespace

from minmax.build_candidate import BuildCandidate, BuildChange
from models.build_model import ARMOR_SLOTS, PlayerBuild
from services.extreme_actual_heal_armor_weight_candidate_service import (
    ExtremeActualHealArmorWeightCandidateService,
)


class _Legality:
    def __init__(self, options, *, unresolved_by_slot=None):
        self.options = tuple(options)
        self.unresolved_by_slot = unresolved_by_slot or {}

    def evaluate(self, build):
        _ = build
        rows = tuple(
            SimpleNamespace(
                slot=slot,
                allowed_weights=tuple(self.options[index]),
                unresolved=tuple(self.unresolved_by_slot.get(slot, ())),
            )
            for index, slot in enumerate(ARMOR_SLOTS)
        )
        return SimpleNamespace(slots=rows)


def _build(weight="Light"):
    build = PlayerBuild(BuildName="Armor frontier")
    for slot in ARMOR_SLOTS:
        build.Armor[slot]["Weight"] = weight
    return build


def test_all_three_weight_slots_reduce_2187_layouts_to_14_h1_signatures():
    service = ExtremeActualHealArmorWeightCandidateService(
        _Legality((("Light", "Medium", "Heavy"),) * len(ARMOR_SLOTS))
    )

    result = service.build_candidates(
        _build("Light"),
        character_id="char-1",
        baseline_build_id="build-1",
    )

    assert result.denominator_proven is True
    assert result.raw_layout_count == 3 ** 7
    assert result.retained_signature_count == 14
    assert len(result.candidates) == 13  # existing 7-Light witness is already present
    signatures = {
        (
            change.after["medium_piece_count"],
            change.after["distinct_armor_type_count"],
        )
        for candidate in result.candidates
        for change in candidate.changes
        if change.path == "Armor.WeightComposition"
    }
    assert (7, 1) in signatures
    assert (1, 3) in signatures
    assert (0, 2) in signatures


def test_fixed_named_set_weights_shrink_raw_denominator_before_signature_reduction():
    options = [
        ("Light",),
        ("Light",),
        ("Medium", "Heavy"),
        ("Medium", "Heavy"),
        ("Light", "Medium", "Heavy"),
        ("Light", "Medium", "Heavy"),
        ("Light", "Medium", "Heavy"),
    ]
    service = ExtremeActualHealArmorWeightCandidateService(_Legality(options))

    result = service.build_candidates(
        _build("Light"),
        character_id="char-1",
        baseline_build_id="build-1",
    )

    assert result.denominator_proven is True
    assert result.raw_layout_count == 1 * 1 * 2 * 2 * 3 * 3 * 3
    assert result.retained_signature_count < result.raw_layout_count


def test_expanding_gear_candidate_preserves_original_changes():
    options = (("Medium",),) * len(ARMOR_SLOTS)
    service = ExtremeActualHealArmorWeightCandidateService(_Legality(options))
    build = _build("Light")
    build.Armor["Chest"]["Set"] = "Some Medium Set"
    original_change = BuildChange.from_values(
        path="Armor.PrimaryFivePieceSet",
        before="Old",
        after="Some Medium Set",
        source="test",
    )
    candidate = BuildCandidate.from_build(
        character_id="char-1",
        baseline_build_id="build-1",
        candidate_id="gear-candidate",
        candidate_build=build,
        changes=(original_change,),
        candidate_source="test:gear",
    )

    result = service.expand_candidate(candidate)

    assert result.denominator_proven is True
    assert len(result.candidates) == 1
    expanded = result.candidates[0]
    assert expanded.changes[0] == original_change
    assert expanded.changes[-1].path == "Armor.WeightComposition"
    assert all(
        expanded.candidate_build.Armor[slot]["Weight"] == "Medium"
        for slot in ARMOR_SLOTS
    )


def test_unresolved_slot_evidence_blocks_frontier_instead_of_guessing():
    unresolved = {"Chest": ("missing canonical armor weight",)}
    service = ExtremeActualHealArmorWeightCandidateService(
        _Legality((("Light", "Medium", "Heavy"),) * len(ARMOR_SLOTS), unresolved_by_slot=unresolved)
    )

    result = service.build_candidates(
        _build("Light"),
        character_id="char-1",
        baseline_build_id="build-1",
    )

    assert result.denominator_proven is False
    assert result.candidates == ()
    assert result.unresolved == ("missing canonical armor weight",)
