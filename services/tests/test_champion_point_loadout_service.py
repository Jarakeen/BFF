from services.champion_point_loadout_service import (
    CHAMPION_POINT_SLOTS_PER_DISCIPLINE,
    ChampionPointLoadoutCandidate,
    ChampionPointLoadoutService,
    ChampionPointSlotCandidate,
)


def _candidate(name, discipline, ceiling, condition=None):
    return ChampionPointLoadoutCandidate(
        name=name,
        discipline_index=discipline,
        flat_ceiling=ceiling,
        condition=condition,
    )


def _slot(name, discipline):
    return ChampionPointSlotCandidate(name=name, discipline_index=discipline)


def test_selects_additive_top_four_per_discipline_and_keeps_other_disciplines():
    result = ChampionPointLoadoutService.build(
        (
            _candidate("A", 1, 500.0),
            _candidate("B", 1, 400.0),
            _candidate("C", 1, 300.0),
            _candidate("D", 1, 200.0),
            _candidate("E", 1, 100.0),
            _candidate("Other Tree", 2, 90.0),
        )
    )

    assert CHAMPION_POINT_SLOTS_PER_DISCIPLINE == 4
    assert [row.name for row in result.selected] == [
        "A",
        "B",
        "C",
        "D",
        "Other Tree",
    ]
    assert [row.name for row in result.excluded] == ["E"]
    assert result.discipline_slot_counts == ((1, 4), (2, 1))
    assert result.total_flat_ceiling == 1490.0
    assert result.denominator_proven is True


def test_equal_ceilings_have_deterministic_name_tie_break():
    result = ChampionPointLoadoutService.build(
        tuple(_candidate(name, 0, 100.0) for name in ("Echo", "Delta", "Charlie", "Bravo", "Alpha"))
    )

    assert [row.name for row in result.selected] == ["Alpha", "Bravo", "Charlie", "Delta"]
    assert [row.name for row in result.excluded] == ["Echo"]


def test_runtime_condition_is_preserved_without_being_claimed_as_active():
    result = ChampionPointLoadoutService.build(
        (_candidate("Peace of Mind", 1, 200.0, "while under Crowd Control Immunity"),)
    )

    assert result.selected[0].condition == "while under Crowd Control Immunity"
    assert result.denominator_proven is True


def test_missing_discipline_identity_fails_closed():
    result = ChampionPointLoadoutService.build(
        (_candidate("Mystery", None, 100.0),)
    )

    assert result.selected == ()
    assert result.denominator_proven is False
    assert "discipline identity" in result.unresolved[0]


def test_duplicate_identity_fails_closed():
    result = ChampionPointLoadoutService.build(
        (_candidate("Rejuvenation", 1, 90.0), _candidate("rejuvenation", 1, 90.0))
    )

    assert result.denominator_proven is False
    assert "duplicate" in result.unresolved[0]


def test_mixed_unit_enumeration_keeps_all_relevant_stars_when_four_or_fewer():
    result = ChampionPointLoadoutService.enumerate_legal_loadouts(
        (
            _slot("Flat Power", 1),
            _slot("Healing Done", 1),
            _slot("Critical Healing", 1),
            _slot("Other Discipline", 2),
        )
    )

    assert result.denominator_proven is True
    assert result.candidate_count == 4
    assert result.discipline_candidate_counts == ((1, 3), (2, 1))
    assert len(result.loadouts) == 1
    assert [row.name for row in result.loadouts[0]] == [
        "Critical Healing",
        "Flat Power",
        "Healing Done",
        "Other Discipline",
    ]


def test_mixed_unit_enumeration_emits_every_four_star_combination():
    result = ChampionPointLoadoutService.enumerate_legal_loadouts(
        tuple(_slot(name, 1) for name in ("A", "B", "C", "D", "E"))
    )

    assert result.denominator_proven is True
    assert len(result.loadouts) == 5
    assert {tuple(row.name for row in loadout) for loadout in result.loadouts} == {
        ("A", "B", "C", "D"),
        ("A", "B", "C", "E"),
        ("A", "B", "D", "E"),
        ("A", "C", "D", "E"),
        ("B", "C", "D", "E"),
    }


def test_mixed_unit_enumeration_fails_closed_on_missing_discipline():
    result = ChampionPointLoadoutService.enumerate_legal_loadouts(
        (_slot("Mystery", None),)
    )

    assert result.denominator_proven is False
    assert result.loadouts == ()
    assert "discipline identity" in result.unresolved[0]
