from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.uesp.uesp_client import UespClient
from services.uesp.uesp_parser import (
    UespParser,
    parse_page_html,
    _section,
    _extract_dialogue,
    _group_dialogue_by_trigger,
    _match_dialogue_trigger_to_ability,
    DIALOGUE_HEADINGS,
)

client = UespClient(
    REPO_ROOT / "data" / "uesp" / ".cache"
)

page = client.get_page("Online:Oaxiltso")

print("TITLE:", page.title)

# --------------------------------------------------
# Raw parsed infobox
# --------------------------------------------------

parsed = parse_page_html(page.html)



print()
print("========== INFOBOX ==========")

for key, value in parsed.infobox.items():
    print(f"{key!r}: {value!r}")

# --------------------------------------------------
# Parsed boss
# --------------------------------------------------

parser = UespParser()

boss = parser.parse_boss(
    page,
    content_id="rockgrove",
    content_name="Rockgrove",
)

print()
print("========== BOSS ==========")
print("NAME:", boss.name)
print("HEALTH:", boss.health)
print("ABILITIES:", len(boss.abilities))
print("MECHANICS:", len(boss.mechanics))
print("DIALOGUE:", len(boss.dialogue))
print("ACHIEVEMENTS:", len(boss.achievements))

print()
print("========== PHASES ==========")

for phase in boss.phases:
    print("LABEL:", phase.label)
    print("THRESHOLD:", phase.threshold)
    print("DESCRIPTION:", phase.description)


print()
print("========== SECTION NAMES ==========")

for heading in parsed.sections:
    print(repr(heading))

parsed = parse_page_html(page.html)

infobox = parsed.infobox

dialogue_blocks = _section(
    parsed.sections,
    DIALOGUE_HEADINGS,
) or []

dialogue = _extract_dialogue(dialogue_blocks)

dialogue_by_trigger = _group_dialogue_by_trigger(dialogue)
print()
print("========== BOSS DIALOGUE BY TRIGGER ==========")


# Health specifically
# --------------------------------------------------
print()
print()
print()
print("========== TRIGGER → ABILITY MATCHES ==========")

for trigger in dialogue_by_trigger:
    matched = _match_dialogue_trigger_to_ability(
        trigger,
        dialogue_by_trigger[trigger],
        boss.abilities,
    )

    print(f"{trigger} -> {matched}")

print()
print("========== HEALTH ==========")
print("Normal:", boss.health.normal)
print("Veteran:", boss.health.veteran)
print("Hardmode:", boss.health.hardmode)

print()
print("========== SKILLS AND ABILITIES ==========")

for block in parsed.sections.get("Skills and Abilities", []):
    print(block)

print()
print("========== QUEST-RELATED EVENTS ==========")

for block in parsed.sections.get("Quest-Related Events", []):
    print(block)