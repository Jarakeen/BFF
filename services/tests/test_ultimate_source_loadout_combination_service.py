from __future__ import annotations

from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibility,
)
from services.ultimate_source_loadout_combination_service import (
    UltimateSourceLoadoutCandidate,
    UltimateSourceLoadoutCombinationService,
)


_ALL_ARMOR = ("Chest", "Feet", "Hands", "Head", "Legs", "Shoulders", "Waist")
_ALL_JEWELRY = ("Necklace", "Ring")
_ALL_WEAPONS = (
    "Axe",
    "Bow",
    "Dagger",
    "Ice Staff",
    "Inferno Staff",
    "Lightning Staff",
    "Mace",
    "Restoration Staff",
    "Shield",
    "Sword",
    "Two-Handed Axe",
    "Two-Handed Mace",
    "Two-Handed Sword",
)


def _set(
    set_id: int,
    name: str,
    *,
    armor_slots: tuple[str, ...] = _ALL_ARMOR,
    jewelry_slots: tuple[str, ...] = _ALL_JEWELRY,
    weapon_types: tuple[str, ...] = _ALL_WEAPONS,
    max_equip_count: int = 5,
) -> ExtremeNamedGearSetSlotEligibility:
    return ExtremeNamedGearSetSlotEligibility(
        set_id=set_id,
        name=name,
        category="monster" if max_equip_count == 2 else "dungeon",
        max_equip_count=max_equip_count,
        armor_slots=armor_slots,
        jewelry_slots=jewelry_slots,
        weapon_types=weapon_types,
    )


def _candidates() -> tuple[UltimateSourceLoadoutCandidate, ...]:
    return (
        UltimateSourceLoadoutCandidate(
            "bloodspawn",
            "Bloodspawn",
            65,
            "Bloodspawn",
            2,
            stochastic=True,
        ),
        UltimateSourceLoadoutCandidate(
            "baron_zaudrus",
            "Baron Zaudrus",
            96,
            "Baron Zaudrus",
            2,
            action_proof_required=True,
        ),
        UltimateSourceLoadoutCandidate(
            "hide_of_the_werewolf",
            "Hide of the Werewolf",
            30,
            "Hide of the Werewolf",
            5,
        ),
        UltimateSourceLoadoutCandidate(
            "arkasis",
            "Arkasis's Genius",
            44,
            "Arkasis's Genius",
            5,
        ),
        UltimateSourceLoadoutCandidate(
            "arkays_charity",
            "Arkay's Charity",
            39,
            "Arkay's Charity",
            5,
        ),
        UltimateSourceLoadoutCandidate(
            "decisive",
            "Decisive",
            40,
            stochastic=True,
        ),
    )


def _sets() -> tuple[ExtremeNamedGearSetSlotEligibility, ...]:
    monster_slots = ("Head", "Shoulders")
    return (
        _set(
            1,
            "Bloodspawn",
            armor_slots=monster_slots,
            jewelry_slots=(),
            weapon_types=(),
            max_equip_count=2,
        ),
        _set(
            2,
            "Baron Zaudrus",
            armor_slots=monster_slots,
            jewelry_slots=(),
            weapon_types=(),
            max_equip_count=2,
        ),
        _set(3, "Hide of the Werewolf"),
        _set(4, "Arkasis's Genius"),
        _set(5, "Arkay's Charity"),
    )


def _catalog(named_sets: tuple[ExtremeNamedGearSetSlotEligibility, ...] | None = None):
    return UltimateSourceLoadoutCombinationService.search(
        _candidates(),
        _sets() if named_sets is None else named_sets,
        required_ultimate_gap=110,
    )


def _row(catalog, *source_ids: str):
    wanted = tuple(sorted(source_ids))
    return next(row for row in catalog.combinations if row.source_ids == wanted)


def test_all_63_non_empty_subsets_are_accounted_for() -> None:
    catalog = _catalog()

    assert len(catalog.candidates) == 6
    assert len(catalog.combinations) == 63
    assert len(catalog.legal_combinations) + len(catalog.rejected_combinations) == 63
    assert catalog.physical_set_slot_denominator_proven is True


def test_exact_five_five_two_witness_is_retained() -> None:
    catalog = _catalog()
    row = _row(catalog, "arkasis", "bloodspawn", "hide_of_the_werewolf")

    assert row.required_set_units == 12
    assert row.physically_legal is True
    assert row.witness is not None
    assert row.witness.counts == (5, 5, 2)
    assert set(row.witness.set_names) == {
        "Arkasis's Genius",
        "Bloodspawn",
        "Hide of the Werewolf",
    }


def test_competing_monster_sets_are_rejected_by_exact_slot_realization() -> None:
    catalog = _catalog()
    row = _row(catalog, "baron_zaudrus", "bloodspawn")

    assert row.required_set_units == 4
    assert row.physically_legal is False
    assert row.witness is None
    assert "no witness" in row.rejection_reason


def test_three_five_piece_sets_are_rejected_before_realization() -> None:
    catalog = _catalog()
    row = _row(catalog, "arkasis", "arkays_charity", "hide_of_the_werewolf")

    assert row.required_set_units == 15
    assert row.physically_legal is False
    assert "canonical snapshot limit is 12" in row.rejection_reason


def test_decisive_overlays_legal_named_sets_but_remains_stochastic() -> None:
    catalog = _catalog()
    row = _row(catalog, "arkasis", "decisive", "hide_of_the_werewolf")

    assert row.required_set_units == 10
    assert row.total_ultimate_ceiling == 114
    assert row.physically_legal is True
    assert row.closes_gap is True
    assert row.stochastic is True
    assert row.runtime_proven is False


def test_missing_named_set_evidence_fails_denominator_closed() -> None:
    named_sets = tuple(row for row in _sets() if row.name != "Arkay's Charity")
    catalog = _catalog(named_sets)
    row = _row(catalog, "arkays_charity")

    assert catalog.physical_set_slot_denominator_proven is False
    assert catalog.unresolved
    assert row.physically_legal is False
    assert "no exact named-set eligibility" in row.rejection_reason


def test_no_gap_closing_branch_is_promoted_to_runtime_proven() -> None:
    catalog = _catalog()

    assert catalog.gap_closing_combinations
    assert catalog.minimal_gap_closing_combinations
    assert not any(row.runtime_proven for row in catalog.gap_closing_combinations)
