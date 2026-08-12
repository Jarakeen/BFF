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

client = UespClient(REPO_ROOT / "data" / "uesp" / ".cache")
page = client.get_page("Online:Oaxiltso")

print("TITLE:", page.title)

parsed = parse_page_html(page.html)

print()
print("========== INFOBOX ==========")
for key, value in parsed.infobox.items():
    print(f"{key!r}: {value!r}")

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
print("========== DIALOGUE BY TRIGGER ==========")
for trigger, lines in boss.dialogue_by_trigger.items():
    print()
    print(f"[{trigger}]")
    for entry in lines:
        print(f"  {entry.speaker}: {entry.line}")
        print(f"    ABILITY: {entry.ability}")

print()
print("========== TRIGGER → ABILITY MATCHES ==========")
for trigger, lines in boss.dialogue_by_trigger.items():
    matched = lines[0].ability if lines else None
    print(f"{trigger} -> {matched}")

print()
print("========== HEALTH ==========")
print("Normal:", boss.health.normal)
print("Veteran:", boss.health.veteran)
print("Hardmode:", boss.health.hardmode)

print()
print("========== SKILLS AND ABILITIES ==========")
for ability in boss.abilities:
    print(f"{ability.name}: {ability.description}")
