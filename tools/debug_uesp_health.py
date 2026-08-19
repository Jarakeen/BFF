from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.uesp.uesp_client import UespClient
from services.uesp.uesp_parser import parse_page_html


CACHE_DIR = ROOT / "data" / "uesp" / ".cache"

BOSSES = [
    "Online:Lokkestiiz",
    "Online:Yolnahkriin",
    "Online:Nahviintaas",
]

client = UespClient(cache_dir=CACHE_DIR)

for title in BOSSES:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)

    page = client.get_page(title)
    parsed = parse_page_html(page.html)

    print("\nINFOBOX HEALTH FIELDS:")
    for key, value in parsed.infobox.items():
        if "health" in key.lower():
            print(repr(key), "=>", repr(value))

    print("\nALL INFOBOX FIELDS:")
    for key, value in parsed.infobox.items():
        print(repr(key), "=>", repr(value))

    print("\nHEALTH/VETERAN/HARDMODE BLOCKS:")
    for block in parsed.all_blocks:
        text = block.get("text", "")
        lowered = text.lower()

        if (
            "health" in lowered
            or "veteran" in lowered
            or "hardmode" in lowered
            or "hard mode" in lowered
        ):
            print(block)