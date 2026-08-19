from services.uesp.enriched_parser import EnrichedUespParser
from services.uesp.uesp_parser import slugify
from services.uesp.uesp_client import UespPage

SAMPLE_BOSS_HTML = """
<table class="wikitable">
<tr><th>Location</th><td>Rockgrove, Tower of the Five Crimes</td></tr>
<tr><th>Species</th><td>Harvester</td></tr>
<tr><th>Reaction</th><td>Hostile</td></tr>
<tr><th>Health</th><td>25,084,768<br>53,558,256<br>214,233,024 (Hard Mode)</td></tr>
</table>
<p>Xalvakka is the final boss of Rockgrove.</p>
<h2>Skills and Abilities</h2>
<dl>
<dt>Scathing Evisceration</dt>
<dd>Xalvakka performs five claw swipes, dealing massive combined flame damage. This can be blocked.</dd>
<dt>Deadstar</dt>
<dd>Creates an area attack that deals flame damage and leaves a lingering hazard.</dd>
</dl>
<h2>Strategy</h2>
<p>The fight has three phases. Phase 2 begins when the boss reaches 70% health.</p>
<p>Stay aware of the arena and keep the group positioned safely.</p>
<h2>Quest-Related Events</h2>
<p>As the fight starts:</p>
<ul><li>Xalvakka: "Drown in fire!"</li></ul>
<p>At 70%:</p>
<ul><li>Xalvakka: "Yes! Give chase, my morsels!"</li></ul>
<h2>Achievements</h2>
<ul><li><a href="/wiki/Online:Rockgrove_Vanquisher">Rockgrove Vanquisher</a></li></ul>
<h2>Notes</h2>
<ul>
<li>Xalvakka's corpse will appear outside the Oblivion Gate if you don't loot her in time.</li>
<li>You will receive a Cinder Ash Plate for defeating Xalvakka with Hard Mode active.</li>
</ul>
"""


def sample_page(html=SAMPLE_BOSS_HTML, revision_id=42):
    return UespPage(
        title="Online:Xalvakka",
        page_id=1,
        revision_id=revision_id,
        wikitext="",
        html=html,
        categories=["Online-Bosses"],
    )


def test_enriched_parser_preserves_core_boss_facts():
    boss = EnrichedUespParser().parse_boss(sample_page())
    assert boss.location == "Rockgrove, Tower of the Five Crimes"
    assert boss.species == "Harvester"
    assert boss.reaction == "Hostile"
    assert boss.health.normal == "25,084,768"
    assert boss.health.veteran == "53,558,256"
    assert "214,233,024" in boss.health.hardmode


def test_enriched_parser_extracts_strategy_phase():
    boss = EnrichedUespParser().parse_boss(sample_page())
    phase = next(phase for phase in boss.phases if phase.label == "Phase 2")
    assert phase.threshold == "70%"


def test_enriched_parser_extracts_li_dialogue_and_trigger_context():
    boss = EnrichedUespParser().parse_boss(sample_page())
    assert len(boss.dialogue) == 2
    assert boss.dialogue[0].speaker == "Xalvakka"
    assert "Drown in fire" in boss.dialogue[0].line
    assert boss.dialogue[0].trigger == "As the fight starts:"
    assert boss.dialogue[1].trigger == "At 70%:"


def test_enriched_parser_extracts_achievements_and_notes():
    boss = EnrichedUespParser().parse_boss(sample_page())
    assert len(boss.achievements) == 1
    assert boss.achievements[0].name == "Rockgrove Vanquisher"
    assert boss.achievements[0].id == "rockgrove_vanquisher"
    assert len(boss.notes) == 2


def test_enriched_parser_classifies_ability_mechanics_without_replacing_source_text():
    boss = EnrichedUespParser().parse_boss(sample_page())
    flame = next(mechanic for mechanic in boss.mechanics if mechanic.name == "Deadstar")
    assert flame.mechanic_type == "area_attack"
    assert flame.damage_type == "flame"
    assert flame.interpretation_status == "inferred"
    assert "lingering hazard" in flame.description


def test_slugify_behavior_remains_unchanged():
    assert slugify("Online:Xalvakka") == "xalvakka"
    assert slugify("Online:Ash Titan (Rockgrove)") == "ash_titan_rockgrove"
