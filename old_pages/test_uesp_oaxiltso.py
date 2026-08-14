from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.uesp.uesp_client import UespClient
from services.uesp.uesp_parser import UespParser


CACHE = REPO_ROOT / "data" / "uesp" / ".cache"
EXPECTED_ABILITIES = 8
EXPECTED_DIALOGUE = 15


def main() -> None:
    client = UespClient(CACHE)
    page = client.get_page("Online:Oaxiltso")

    parser = UespParser()
    first = parser.parse_boss(
        page,
        content_id="rockgrove",
        content_name="Rockgrove",
    )
    second = parser.parse_boss(
        page,
        content_id="rockgrove",
        content_name="Rockgrove",
    )

    assert first.id == "oaxiltso"
    assert first.name == "Oaxiltso"
    assert first.content_id == "rockgrove"
    assert first.content_name == "Rockgrove"
    assert len(first.abilities) == EXPECTED_ABILITIES, (
        f"Expected {EXPECTED_ABILITIES} abilities, got {len(first.abilities)}"
    )
    assert len(first.dialogue) == EXPECTED_DIALOGUE, (
        f"Expected {EXPECTED_DIALOGUE} dialogue lines, got {len(first.dialogue)}"
    )

    # Every parsed mechanic must now have an explicit name. Blank names are
    # a schema failure, not something we should quietly accept into the KB.
    assert all(mechanic.name.strip() for mechanic in first.mechanics), (
        "At least one mechanic has no explicit name"
    )

    # Parsing the same source twice must be deterministic. This catches
    # accidental mutation or order-dependent extraction logic.
    assert first == second, "Oaxiltso parsing is not deterministic"

    # The source record must remain traceable to UESP.
    assert first.source is not None
    assert first.source.page_title == page.title
    assert first.source.url.endswith("Online:Oaxiltso")

    print("OAXILTSO TEST PASSED")
    print(f"  title:      {page.title}")
    print(f"  abilities:  {len(first.abilities)}")
    print(f"  mechanics:  {len(first.mechanics)}")
    print(f"  dialogue:   {len(first.dialogue)}")
    print(f"  health:     {first.health}")
    print(f"  source rev: {first.source.revision_id}")
    print("  deterministic: yes")


if __name__ == "__main__":
    main()
