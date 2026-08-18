from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.uesp.uesp_client import UespClient
from services.uesp.uesp_parser import parse_page_html


CACHE_DIR = ROOT / "data" / "uesp" / ".cache"

client = UespClient(cache_dir=CACHE_DIR)

page = client.get_page("Online:Sunspire")
parsed = parse_page_html(page.html)

print("=" * 70)
print("ONLINE:SUNSPIRE")
print("=" * 70)

print("\nSECTIONS:")
for heading in parsed.sections:
    print(repr(heading))

print("\nACHIEVEMENT SECTIONS:")
for heading, blocks in parsed.sections.items():
    if "achievement" in heading.lower():
        print(f"\nSECTION: {heading}")
        for block in blocks:
            print(block)

print("\nREWARD / LOOT / SET / ITEM SECTIONS:")
for heading, blocks in parsed.sections.items():
    lowered = heading.lower()
    if any(
        term in lowered
        for term in ("reward", "loot", "set", "item", "drop")
    ):
        print(f"\nSECTION: {heading}")
        for block in blocks:
            print(block)

print("\nLINKS THAT LOOK LIKE ITEMS/SETS:")
for block in parsed.all_blocks:
    for href, text in block.get("links", []):
        lowered = (href + " " + text).lower()
        if any(
            term in lowered
            for term in ("set", "item", "armor", "gear")
        ):
            print(href, "=>", repr(text))
            