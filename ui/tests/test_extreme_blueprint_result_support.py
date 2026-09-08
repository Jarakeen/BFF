from pathlib import Path

from ui import extreme_blueprint_result_support


def test_reviewed_class_mastery_note_becomes_result_row() -> None:
    row = extreme_blueprint_result_support._reviewed_mastery_row(
        (
            "Best currently reviewed pure-class mastery route for Weapon Damage: "
            "Sorcerer with Mastery A + Mastery B; projected mastery-only delta 123 under reviewed conditions.",
        )
    )

    assert row == (
        "Class Mastery (reviewed)",
        "Sorcerer with Mastery A + Mastery B",
    )


def test_no_reviewed_mastery_route_does_not_invent_row() -> None:
    assert extreme_blueprint_result_support._reviewed_mastery_row(
        ("Reviewed pure-class Class Mastery scoring currently has no numeric route for Maximum Health.",)
    ) is None


def test_result_support_wires_food_ties_and_mastery_rows() -> None:
    source = Path(extreme_blueprint_result_support.__file__).read_text(encoding="utf-8")

    assert "extreme_food_winners(" in source
    assert 'rows.insert(food_index + 1, ("Food co-winners", co_winners))' in source
    assert 'return "Class Mastery (reviewed)", route' in source
