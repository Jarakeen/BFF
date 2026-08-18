from services.uesp.enriched_parser import EnrichedUespParser as UespParser
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


def _sample_page(html: str = SAMPLE_BOSS_HTML, revision_id: int = 42) -> UespPage:
    return UespPage(
        title="Online:Xalvakka",
        page_id=1,
        revision_id=revision_id,
        wikitext="",
        html=html,
        categories=["Online-Bosses"],
    )


def test_slugify_strips_namespace():
    assert slugify("Online:Xalvakka") == "xalvakka"


def test_slugify_keeps_disambiguator_for_uniqueness():
    assert slugify("Online:Ash Titan (Rockgrove)") == "ash_titan_rockgrove"


def test_slugify_handles_plain_titles_without_namespace():
    assert slugify("Bahsei") == "bahsei"


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


def test_parse_boss_abilities():
    boss = UespParser().parse_boss(_sample_page())
    names = [ability.name for ability in boss.abilities]
    assert names == ["Scathing Evisceration", "Deadstar"]
    evisceration = boss.abilities[0]
    assert "claw swipes" in evisceration.description
    assert "blocked" in evisceration.description


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


def test_parse_boss_dialogue_with_trigger_context():
    boss = UespParser().parse_boss(_sample_page())
    assert len(boss.dialogue) == 2
    assert boss.dialogue[0].speaker == "Xalvakka"
    assert "Drown in fire" in boss.dialogue[0].line
    assert boss.dialogue[0].trigger == "As the fight starts:"
    assert boss.dialogue[1].trigger == "At 70%:"


def test_parse_boss_notes():
    boss = UespParser().parse_boss(_sample_page())
    assert len(boss.notes) == 2
    assert any("Cinder Ash Plate" in note for note in boss.notes)


def test_parse_boss_achievement_links():
    boss = UespParser().parse_boss(_sample_page())
    assert len(boss.achievements) == 1
    assert boss.achievements[0].name == "Rockgrove Vanquisher"
    assert boss.achievements[0].id == "rockgrove_vanquisher"


def test_parse_boss_hardmode_info_extracted_from_prose():
    boss = UespParser().parse_boss(_sample_page())
    assert any("Hard Mode" in sentence for sentence in boss.difficulty_notes.hardmode_info)


def test_parse_boss_records_source_metadata():
    boss = UespParser().parse_boss(_sample_page())
    assert boss.source is not None
    assert boss.source.page_title == "Online:Xalvakka"
    assert boss.source.revision_id == 42


def test_parse_boss_never_invents_missing_sections():
    boss = UespParser().parse_boss(_sample_page("<p>A minimal test boss page with no other sections.</p>"))
    assert boss.abilities == []
    assert boss.phases == []
    assert boss.dialogue == []
    assert boss.achievements == []


def test_detect_content_type():
    page = _sample_page()
    page.categories = ["Online-Places-Trials"]
    assert UespParser().detect_content_type(page, "dungeon") == "trial"


def test_parse_boss_related_information():
    boss = UespParser().parse_boss(_sample_page())
    assert boss.summary
    assert boss.source is not None

def test_parse_boss_health_repeated_veteran_marker_identifies_hardmode():
    html = """
    <table class="infobox">
        <tr>
            <th>Health</th>
            <td>
                <a href="/wiki/File:ON-icon-Normal.png"></a>18,177,368
                <br>
                <a href="/wiki/Online:Veteran"></a>77,620,640
                <br>
                <a href="/wiki/Online:Veteran"></a>97,025,800 (Hardmode)
            </td>
        </tr>
    </table>
    """

    boss = UespParser().parse_boss(_sample_page(html))

    assert boss.health.normal == "18,177,368"
    assert boss.health.veteran == "77,620,640"
    assert boss.health.hardmode == "97,025,800 (Hardmode)"


def test_parse_boss_health_separate_hardmode_paragraph():
    html = """
    <table class="infobox">
        <tr>
            <th>Health</th>
            <td>
                <a href="/wiki/File:ON-icon-Normal.png"></a>22,721,708
                <br>
                <a href="/wiki/Online:Veteran"></a>116,430,960
            </td>
        </tr>
    </table>

    <p>
        <a href="/wiki/Online:Veteran"></a>145,538,704 (hard mode)
    </p>
    """

    boss = UespParser().parse_boss(_sample_page(html))

    assert boss.health.normal == "22,721,708"
    assert boss.health.veteran == "116,430,960"
    assert boss.health.hardmode == "145,538,704"