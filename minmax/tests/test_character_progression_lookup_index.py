from minmax.character_progression import CharacterProgression


def test_progression_builds_casefolded_lookup_indexes_without_changing_public_names() -> None:
    progression = CharacterProgression(
        owned_skill_lines=(" Fighters Guild ", "Undaunted"),
        passive_ranks={" Slayer ": 3, "Undaunted Mettle": 2},
        passive_cp_points={" Fortification ": 30},
    )

    assert progression.owned_skill_lines == ("Fighters Guild", "Undaunted")
    assert progression.passive_ranks == {"Slayer": 3, "Undaunted Mettle": 2}
    assert progression.passive_cp_points == {"Fortification": 30}

    assert progression._owned_skill_line_lookup == frozenset({"fighters guild", "undaunted"})
    assert progression._passive_rank_lookup == {"slayer": 3, "undaunted mettle": 2}
    assert progression._passive_cp_lookup == {"fortification": 30}


def test_progression_queries_preserve_case_and_whitespace_insensitive_semantics() -> None:
    progression = CharacterProgression(
        owned_skill_lines=("Fighters Guild",),
        passive_ranks={"Undaunted Mettle": 2, "Slayer": 3},
        passive_cp_points={"Fortification": 30},
    )

    assert progression.owns_skill_line("  fighters guild  ") is True
    assert progression.passive_rank("  UNDAUNTED   METTLE ") == 2
    assert progression.passive_rank(" slayer ") == 3
    assert progression.passive_cp_allocation(" FORTIFICATION ") == 30
    assert progression.passive_rank("Missing Passive") is None
    assert progression.passive_cp_allocation("Missing CP") is None


def test_unknown_progression_maps_remain_distinct_from_explicit_empty_maps() -> None:
    unknown = CharacterProgression(passive_ranks=None, passive_cp_points=None)
    explicit_empty = CharacterProgression(passive_ranks={}, passive_cp_points={})

    assert unknown.passive_ranks is None
    assert unknown.passive_cp_points is None
    assert unknown._passive_rank_lookup is None
    assert unknown._passive_cp_lookup is None
    assert unknown.passive_rank("Slayer") is None
    assert unknown.passive_cp_allocation("Fortification") is None

    assert explicit_empty.passive_ranks == {}
    assert explicit_empty.passive_cp_points == {}
    assert explicit_empty._passive_rank_lookup == {}
    assert explicit_empty._passive_cp_lookup == {}
    assert explicit_empty.passive_rank("Slayer") is None
    assert explicit_empty.passive_cp_allocation("Fortification") is None
