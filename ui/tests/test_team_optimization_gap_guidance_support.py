from types import SimpleNamespace

from ui.team_optimization_gap_guidance_support import guidance_for_gap, _rows_for_analysis


def test_gap_guidance_points_passive_rank_back_to_character_progression():
    text = guidance_for_gap("Passive rank is not recorded for character: Advanced Species")
    assert "Character Progression" in text


def test_gap_guidance_marks_canonical_effect_failure_as_data_debt():
    text = guidance_for_gap("Champion Point star Foo does not resolve to a canonical effect")
    assert "canonical" in text.casefold() or "evidence" in text.casefold()


def test_gap_rows_preserve_player_build_exact_gap_and_action():
    result = SimpleNamespace(
        build_summaries=(
            SimpleNamespace(
                player_name="Jarakeen",
                build_name="SW Healer",
                capability_gaps=("unknown skill mapping",),
            ),
        )
    )

    rows = _rows_for_analysis(result)

    assert len(rows) == 1
    assert rows[0][0] == "Jarakeen • SW Healer"
    assert rows[0][1] == "unknown skill mapping"
    assert rows[0][2]
