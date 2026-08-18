from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.uesp.uesp_client import UespClient
from services.uesp.uesp_parser import parse_page_html


client = UespClient(cache_dir=ROOT / "data" / "uesp_cache")

page = client.get_page("Online:Oathsworn_Pit")
parsed = parse_page_html(page.html)

print("=" * 70)
print("PAGE")
print("=" * 70)
print(page.title)

print("\n" + "=" * 70)
print("INFOBOX")
print("=" * 70)

for key, value in parsed.infobox.items():
    print(repr(key), "=>", repr(value))

print("\n" + "=" * 70)
print("SECTIONS")
print("=" * 70)

for heading, blocks in parsed.sections.items():
    print(f"\nSECTION: {heading}")

    for block in blocks:
        print(
            " ",
            block.get("type"),
            repr(block.get("text")),
            "LINKS:",
            block.get("links", []),
        )