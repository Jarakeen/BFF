from services.uesp.enriched_parser import EnrichedUespParser
from services.uesp.uesp_client import UespPage


SAMPLE = """
<table>
<tr><td>Location</td><td>Sunspire</td></tr>
<tr><td>Health</td><td>25,084,768<br>53,558,256<br>214,233,024 (Hard Mode)</td></tr>
</table>
<h2>Skills and Abilities</h2>
<dl>
<dt>Flame Burst</dt><dd>Deals flame damage in an area and can be interrupted.</dd>
<dt>Summon</dt><dd>When the boss reaches 50% health, it summons a Behemoth.</dd>
</dl>
<h2>Strategy</h2>
<p>The fight has three phases. Phase 2 begins when the boss reaches 70% health.</p>
<h2>Quest-Related Events</h2>
<p>As the fight starts:</p>
<ul><li>Xalvakka: "Drown in fire!"</li></ul>
<p>At 70%:</p>
<ul><li>Xalvakka: "Give chase!"</li></ul>
"""


def test_enriched_parser_recovers_encounter_facts():
    page = UespPage(
        title="Online:Xalvakka",
        page_id=1,
        revision_id=42,
        wikitext="",
        html=SAMPLE,
        categories=["Online-Bosses"],
    )

    boss = EnrichedUespParser().parse_boss(page)

    assert boss.health.normal == "25,084,768"
    assert boss.health.veteran == "53,558,256"
    assert "214,233,024" in boss.health.hardmode

    phase = next(p for p in boss.phases if p.label == "Phase 2")
    assert phase.threshold == "70%"

    assert len(boss.dialogue) == 2
    assert boss.dialogue[0].speaker == "Xalvakka"
    assert boss.dialogue[0].trigger == "As the fight starts:"

    names = {mechanic.name for mechanic in boss.mechanics}
    assert "Flame Burst" in names
    flame = next(m for m in boss.mechanics if m.name == "Flame Burst")
    assert flame.damage_type == "flame"
    assert flame.mechanic_type == "interrupt"
