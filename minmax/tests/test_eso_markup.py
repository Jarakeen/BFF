from minmax.eso_markup import normalize_eso_markup


def test_single_integer():
    result = normalize_eso_markup("|cffffff5|r")

    assert result.text == "5"
    assert len(result.tokens) == 1
    assert result.tokens[0].raw == "|cffffff5|r"
    assert result.tokens[0].color == "ffffff"
    assert result.tokens[0].value_text == "5"
    assert result.tokens[0].value == 5


def test_multiple_values():
    result = normalize_eso_markup(
        "closest |cffffff5|r members within |cffffff28|r meters"
    )

    assert result.text == "closest 5 members within 28 meters"
    assert [token.value for token in result.tokens] == [5, 28]


def test_decimal():
    result = normalize_eso_markup("|cffffff1.5|r")

    assert result.text == "1.5"
    assert result.tokens[0].value == 1.5


def test_negative_integer():
    result = normalize_eso_markup("|cffffff-10|r")

    assert result.text == "-10"
    assert result.tokens[0].value == -10


def test_zero():
    result = normalize_eso_markup("|cffffff0|r")

    assert result.tokens[0].value == 0


def test_different_color():
    result = normalize_eso_markup("|cff000028|r")

    assert result.text == "28"
    assert result.tokens[0].color == "ff0000"
    assert result.tokens[0].value == 28


def test_mixed_text():
    result = normalize_eso_markup(
        "Gain |cffffff10|r% damage for |cffffff5|r seconds."
    )

    assert result.text == "Gain 10% damage for 5 seconds."
    assert [token.value for token in result.tokens] == [10, 5]


def test_no_markup():
    result = normalize_eso_markup("plain text")

    assert result.text == "plain text"
    assert result.tokens == ()


def test_raw_token_is_preserved():
    result = normalize_eso_markup(
        "value |cABCDEF42|r here"
    )

    token = result.tokens[0]

    assert token.raw == "|cABCDEF42|r"
    assert token.color == "ABCDEF"
    assert token.value_text == "42"
    assert token.value == 42


def test_non_numeric_value_is_preserved():
    result = normalize_eso_markup("|cffffffabc|r")

    assert result.text == "abc"
    assert result.tokens[0].value_text == "abc"
    assert result.tokens[0].value is None


def test_malformed_markup_does_not_crash():
    inputs = [
        "|cffffff5",
        "|cffffff|r",
        "|cffffff|",
        "|cfffffff",
    ]

    for text in inputs:
        result = normalize_eso_markup(text)
        assert isinstance(result.text, str)


def test_master_architect_values():
    text = (
        "(5 items) When you use an Ultimate ability while in combat, "
        "you and the closest |cffffff5|r group members within "
        "|cffffff28|r meters of you gain Major Slayer for "
        "|cffffff1|r second per |cffffff10|r Ultimate spent, "
        "increasing your damage done to Dungeon, Trial, and Arena "
        "Monsters by |cffffff10|r%."
    )

    result = normalize_eso_markup(text)

    assert [token.value for token in result.tokens] == [5, 28, 1, 10, 10]
    assert "|cffffff" not in result.text
    assert "|r" not in result.text
