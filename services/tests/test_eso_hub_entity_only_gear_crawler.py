from __future__ import annotations

from crawlers.eso_hub_entity_only_gear_crawler import parse_set_page


def test_parse_set_page_extracts_focal_arena_bonus_and_modified_skills_only() -> None:
    html = """
    <html><body>
      <h1>Perfected Grand Rejuvenation Set ESO - Stats & Location</h1>
      <div class="tooltip">
        <span>(2 items)</span>
        <span>Adds 877 Maximum Magicka, The initial heal restores resources.</span>
      </div>
      <div>Weapons</div>
      <div><strong>Type:</strong><span>Arena</span></div>
      <div><strong>Location:</strong><span>Dragonstar Arena</span></div>
      <div>This armor set modifies the following skills</div>
      <div><a href="/en/skills/restoration-staff/grand-healing">Grand Healing</a></div>
      <div><a href="/en/skills/restoration-staff/healing-springs">Healing Springs</a></div>
      <div>Champion Points that buff this armor set</div>

      <h2>Other sets in Dragonstar Arena</h2>
      <div>(2 items) Adds 1096 Maximum Stamina</div>
      <div>(3 items) Adds 657 Critical Chance</div>
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
