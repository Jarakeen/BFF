# tests/test_uesp_parser.py
"""
Parser unit tests against fixture HTML modeled on a real UESP boss
page's structure. No network calls - the client is intentionally not
exercised here.
"""

from __future__ import annotations

from services.uesp.uesp_client import UespPage
from services.uesp.uesp_parser import UespParser, slugify


SAMPLE_BOSS_HTML = """
<table class="wikitable">
<tr><th>Location</th><td>Rockgrove, Tower of the Five Crimes</td></tr>
<tr><th>Species</th><td>Harvester</td></tr>
<tr><th>Health</th><td>25,084,768<br>53,558,256<br>214,233,024 (Hard Mode)</td></tr>
<tr><th>Reaction</th><td>Hostile</td></tr>
</table>
<p>Xalvakka is a large Dagonic harvester found in the Tower of the Five Crimes. She serves as the final boss of the trial.</p>
<h2>Related Quests</h2>
<ul><li>Of Stone and Steam: Save the souls of Rockgrove's fallen.</li></ul>
<h2>Skills and Abilities</h2>
<dl>
<dt>Scathing Evisceration</dt>
<dd>Xalvakka performs five claw swipes, dealing massive combined flame damage. This can be blocked.</dd>
<dt>Deadstar</dt>
<dd>Xalvakka conjures three meteors, one after the other, dealing very high flame damage.</dd>
</dl>
<h2>Strategy</h2>
<p>The fight has three phases, each based on how low Xalvakka's health is. Phase 2 starts when Xalvakka's health reaches 70%, and the final phase starts when she hits 40%.</p>
<p>In Veteran mode, you can activate Hard Mode for this fight by activating the Challenge Banner at the end of the bridge.</p>
<h2>Quest-Related Events</h2>
<p>As the fight starts:</p>
<ul><li>Xalvakka: "You cannot win! Drown in fire!"</li></ul>
<p>At 70%:</p>
<ul><li>Xalvakka: "Yes! Give chase, my morsels! Deliver yourselves to me!"</li></ul>
<h2>Achievements</h2>
<ul><li><a href="/wiki/Online:Rockgrove_Vanquisher">Rockgrove Vanquisher</a></li></ul>
<h2>Notes</h2>
<ul>
<li>Xalvakka's corpse will appear outside the Oblivion Gate if you don't loot her in time.</li>
<li>You will receive a Cinder Ash Plate for defeating Xalvakka with Hard Mode active.</li>
</ul>
"""

MINIMAL_HTML = "<p>A minimal test boss page with no other sections.</p>"


def _sample_page(html: str = SAMPLE_BOSS_HTML, revision_id: int = 42) -> UespPage:
    return UespPage(
        title="Online:Xalvakka",
        page_id=1,
        revision_id=revision_id,
        wikitext="",
        html=html,
        categories=["Online-Bosses"],
    )


# --------------------------------------------------
# Slugs
# --------------------------------------------------

def test_slugify_strips_namespace():
    assert slugify("Online:Xalvakka") == "xalvakka"


def test_slugify_keeps_disambiguator_for_uniqueness():
    assert slugify("Online:Ash Titan (Rockgrove)") == "ash_titan_rockgrove"


def test_slugify_handles_plain_titles_without_namespace():
    assert slugify("Bahsei") == "bahsei"


# --------------------------------------------------
# Infobox
# --------------------------------------------------

def test_parse_boss_infobox_fields():
    boss = UespParser().parse_boss(_sample_page())

    assert boss.location == "Rockgrove, Tower of the Five Crimes"
    assert boss.species == "Harvester"
    assert boss.reaction == "Hostile"


def test_parse_boss_health_lines_split_on_br():
    boss = UespParser().parse_boss(_sample_page())

    assert boss.health.normal == "25,084,768"
    assert boss.health.veteran == "53,558,256"
    assert "214,233,024" in boss.health.hardmode
    assert "Hard Mode" in boss.health.hardmode


# --------------------------------------------------
# Abilities
# --------------------------------------------------

def test_parse_boss_abilities():
    boss = UespParser().parse_boss(_sample_page())

    names = [ability.name for ability in boss.abilities]
    assert names == ["Scathing Evisceration", "Deadstar"]

    evisceration = boss.abilities[0]
    assert "claw swipes" in evisceration.description
    assert "blocked" in evisceration.description


# --------------------------------------------------
# Phases
# --------------------------------------------------

def test_parse_boss_phases_from_strategy_text():
    boss = UespParser().parse_boss(_sample_page())

    labels = [phase.label for phase in boss.phases]
    assert "Phase 2" in labels

    phase_2 = next(phase for phase in boss.phases if phase.label == "Phase 2")
    assert phase_2.threshold == "70%"


def test_parse_boss_strategy_notes_preserved_as_paragraphs():
    boss = UespParser().parse_boss(_sample_page())

    assert len(boss.strategy_notes) == 2
    assert "three phases" in boss.strategy_notes[0]


# --------------------------------------------------
# Dialogue
# --------------------------------------------------

def test_parse_boss_dialogue_with_trigger_context():
    boss = UespParser().parse_boss(_sample_page())

    assert len(boss.dialogue) == 2

    assert boss.dialogue[0].speaker == "Xalvakka"
    assert "Drown in fire" in boss.dialogue[0].line
    assert boss.dialogue[0].trigger == "As the fight starts:"

    assert boss.dialogue[1].trigger == "At 70%:"


# --------------------------------------------------
# Notes / quests / achievements
# --------------------------------------------------

def test_parse_boss_notes():
    boss = UespParser().parse_boss(_sample_page())

    assert len(boss.notes) == 2
    assert any("Cinder Ash Plate" in note for note in boss.notes)


def test_parse_boss_related_quests():
    boss = UespParser().parse_boss(_sample_page())

    assert any("Of Stone and Steam" in quest for quest in boss.related_quests)


def test_parse_boss_achievement_links():
    boss = UespParser().parse_boss(_sample_page())

    assert len(boss.achievements) == 1
    assert boss.achievements[0].name == "Rockgrove Vanquisher"
    assert boss.achievements[0].id == "rockgrove_vanquisher"


# --------------------------------------------------
# Difficulty notes
# --------------------------------------------------

def test_parse_boss_hardmode_info_extracted_from_prose():
    boss = UespParser().parse_boss(_sample_page())

    assert any("Hard Mode" in sentence for sentence in boss.difficulty_notes.hardmode_info)


# --------------------------------------------------
# Provenance
# --------------------------------------------------

def test_parse_boss_records_source_metadata():
    boss = UespParser().parse_boss(_sample_page())

    assert boss.source is not None
    assert boss.source.page_title == "Online:Xalvakka"
    assert boss.source.revision_id == 42
    assert boss.source.url == "https://en.uesp.net/wiki/Online:Xalvakka"
    assert boss.source.retrieved_at != ""
    assert "CC BY-SA" in boss.source.license


# --------------------------------------------------
# Never invents missing data
# --------------------------------------------------

def test_parse_boss_never_invents_missing_sections():
    boss = UespParser().parse_boss(_sample_page(html=MINIMAL_HTML))

    assert boss.dialogue == []
    assert boss.abilities == []
    assert boss.phases == []
    assert boss.achievements == []
    assert boss.notes == []
    assert boss.related_quests == []
    assert boss.health.normal == ""
    assert boss.summary == "A minimal test boss page with no other sections."


# --------------------------------------------------
# Content type detection
# --------------------------------------------------

def test_detect_content_type_from_categories():
    parser = UespParser()

    dungeon_page = _sample_page()
    dungeon_page.categories = ["Online-Dungeons", "Online-Places"]
    assert parser.detect_content_type(dungeon_page, default="trial") == "dungeon"

    trial_page = _sample_page()
    trial_page.categories = ["Online-Trials"]
    assert parser.detect_content_type(trial_page, default="dungeon") == "trial"

    unknown_page = _sample_page()
    unknown_page.categories = ["Online-Places"]
    assert parser.detect_content_type(unknown_page, default="arena") == "arena"
