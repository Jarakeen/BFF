from ui.eso_text_cleanup import strip_eso_color_markup


def test_strip_eso_color_markup_preserves_visible_text_starting_with_hex_character() -> None:
    assert strip_eso_color_markup("|c00FF00Fresh selection|r") == "Fresh selection"
    assert strip_eso_color_markup("|cFFAA00Damage bonus|r") == "Damage bonus"
    assert strip_eso_color_markup("|cABCDEFArmor bonus|r") == "Armor bonus"


def test_strip_eso_color_markup_removes_multiple_standard_color_spans() -> None:
    assert (
        strip_eso_color_markup("|cFF0000Red|r and |c00FF00Green|r")
        == "Red and Green"
    )
