from services.team_role_autofill import (
    build_role_compatible_autofill,
    normalize_team_role,
)


def test_healer_listed_first_does_not_fill_main_tank() -> None:
    assignments = build_role_compatible_autofill(
        slot_labels=(
            "Main Tank",
            "Off Tank",
            "Healer 1",
            "Healer 2",
            "DD 1",
            "DD 2",
        ),
        build_roles=("Healer", "Tank", "DD", "Healer", "Tank", "DD"),
    )

    assert [item.build_index for item in assignments] == [1, 4, 0, 3, 2, 5]


def test_unknown_role_is_left_unassigned() -> None:
    assignments = build_role_compatible_autofill(
        slot_labels=("Main Tank", "Healer 1", "DD 1"),
        build_roles=("Crafter", "Healer", "DD"),
    )

    assert [item.build_index for item in assignments] == [None, 1, 2]


def test_support_dd_is_compatible_with_dd_slot_only() -> None:
    assignments = build_role_compatible_autofill(
        slot_labels=("Main Tank", "Healer 1", "DD 1"),
        build_roles=("Support DD", "Tank", "Healer"),
    )

    assert [item.build_index for item in assignments] == [1, 2, 0]


def test_role_normalization_does_not_guess_blank_or_unknown_values() -> None:
    assert normalize_team_role("") is None
    assert normalize_team_role(None) is None
    assert normalize_team_role("Support") is None
