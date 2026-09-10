from parsers import parse_description


def test_parse_description_removes_eso_color_markup_and_preserves_values():
    raw = (
        "Summon a field of flowers which blooms after |cffffff6|r seconds, "
        "healing you and allies in the area for |cffffff3485|r Health.\n\n"
        "While the field grows, you and allies are healed for |cffffff397|r "
        "Health every |cffffff1|r second."
    )

    assert parse_description(raw) == (
        "Summon a field of flowers which blooms after 6 seconds, healing you and "
        "allies in the area for 3485 Health. While the field grows, you and allies "
        "are healed for 397 Health every 1 second."
    )


def test_parse_description_normalizes_eso_markup_before_html_and_entities():
    raw = "Gain <b>|cffffff20|r%</b> &amp; restore |c00ff001234|r Health."

    assert parse_description(raw) == "Gain 20% & restore 1234 Health."
