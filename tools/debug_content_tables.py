from pathlib import Path
import sys
import re

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.uesp.uesp_client import UespClient


client = UespClient(cache_dir=ROOT / "data" / "uesp_cache")

page = client.get_page("Online:Oathsworn_Pit")
html = page.html


print("=" * 80)
print("RAW HTML LENGTH")
print("=" * 80)
print(len(html))


for heading in ["Sets", "Achievements"]:
    print("\n" + "=" * 80)
    print(f"SEARCHING FOR: {heading}")
    print("=" * 80)

    # Find every occurrence of the heading text.
    matches = list(
        re.finditer(
            rf">{re.escape(heading)}<",
            html,
            re.IGNORECASE,
        )
    )

    print("MATCHES:", len(matches))

    for i, match in enumerate(matches[:3]):
        print(f"\n--- MATCH {i + 1} ---")

        start = max(0, match.start() - 1000)
        end = min(len(html), match.end() + 15000)

        print(html[start:end])