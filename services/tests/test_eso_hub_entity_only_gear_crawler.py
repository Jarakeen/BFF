from __future__ import annotations

from crawlers.eso_hub_entity_only_gear_crawler import parse_set_page


def test_parse_set_page_extracts_arena_metadata_bonus_and_modified_skills() -> None:
    html = """
    <html><body>
      <h1>Perfected Grand Rejuvenation Set ESO - Stats & Location</h1>
      <div><strong>Type:</strong><span>Arena</span></div>
      <div><strong>Location:</strong><span>Dragonstar Arena</span></div>
      <div>(2 items) Adds 877 Maximum Magicka, The initial heal restores resources.</div>
      <h2>This armor set modifies the following skills</h2>
      <ul>
        <li><a href="/en/skills/restoration-staff/grand-healing">Grand Healing</a></li>
        <li><a href="/en/skills/restoration-staff/healing-springs">Healing Springs</a></li>
      </ul>
      <h2>Champion Points that buff this armor set</h2>
    </body></html>
    """

    result = parse_set_page(
        html,
        expected_name="Perfected Grand Rejuvenation",
        url="https://eso-hub.com/en/sets/perfected-grand-rejuvenation",
    )

    assert result["type"] == "Arena"
    assert result["location"] == "Dragonstar Arena"
    assert result["bonuses"] == [
        "(2 items) Adds 877 Maximum Magicka, The initial heal restores resources."
    ]
    assert result["modified_skills"] == ["Grand Healing", "Healing Springs"]
    assert result["unresolved"] == []
