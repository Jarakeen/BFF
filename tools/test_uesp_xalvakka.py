from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.uesp.uesp_client import UespClient
from services.uesp.uesp_parser import UespParser
from services.uesp.mechanic_classifier import classify_mechanic

CACHE = REPO_ROOT / "data" / "uesp" / ".cache"
PAGE_TITLE = "Online:Xalvakka"


def main() -> None:
    client = UespClient(CACHE)
    page = client.get_page(PAGE_TITLE)
    parser = UespParser()

    first = parser.parse_boss(page, content_id="rockgrove", content_name="Rockgrove")
    second = parser.parse_boss(page, content_id="rockgrove", content_name="Rockgrove")

    assert first.content_id == "rockgrove"
    assert first.content_name == "Rockgrove"
    assert first.source is not None
    assert first.source.page_title == page.title
    assert first == second, "Xalvakka parsing is not deterministic"
    assert all(ability.name.strip() for ability in first.abilities)
    assert all(mechanic.name.strip() for mechanic in first.mechanics)

    print("XALVAKKA PARSE TEST PASSED")
    print(f"  title:      {page.title}")
    print(f"  abilities:  {len(first.abilities)}")
    print(f"  mechanics:  {len(first.mechanics)}")
    print(f"  dialogue:   {len(first.dialogue)}")
    print(f"  health:     {first.health}")
    print(f"  phases:     {len(first.phases)}")
    print(f"  source rev: {first.source.revision_id}")
    print("  deterministic: yes")

    print("\n========== GENERIC CLASSIFIER PREVIEW ==========")
    for ability in first.abilities:
        result = classify_mechanic(ability.name, ability.description)
        print(f"\n{ability.name}")
        print(f"  type:          {result.mechanic_type}")
        print(f"  damage:        {result.damage_type}")
        print(f"  targets:       {result.target_count}")
        print(f"  movement:      {result.requires_movement}")
        print(f"  positioning:   {result.requires_positioning}")
        print(f"  cleanse:       {result.requires_cleanse}")
        print(f"  hazard:        {result.persistent_hazard}")
        print(f"  interruptible: {result.interruptible}")


if __name__ == "__main__":
    main()
