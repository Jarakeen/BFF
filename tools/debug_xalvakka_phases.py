from __future__ import annotations

import inspect
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.uesp.uesp_client import UespClient
from services.uesp.uesp_parser import UespParser
from services.uesp.phase_extractor import extract_phases

CACHE = REPO_ROOT / "data" / "uesp" / ".cache"
PAGE_TITLE = "Online:Xalvakka"


def main() -> None:
    client = UespClient(CACHE)
    page = client.get_page(PAGE_TITLE)
    parser = UespParser()
    boss = parser.parse_boss(page, content_id="rockgrove", content_name="Rockgrove")

    print("XALVAKKA PHASE EXTRACTION DIAGNOSTIC")
    print(f"  phase_extractor: {inspect.getsourcefile(extract_phases)}")
    print(f"  parsed phases: {[(p.label, p.threshold) for p in boss.phases]}")
    print()
    print("SOURCE BLOCKS CONTAINING PHASE / FINAL PHASE / 40% / 70%")
    parsed = parser.parse_boss(page, content_id="rockgrove", content_name="Rockgrove")
    raw_parser = __import__("services.uesp.uesp_parser", fromlist=["parse_page_html"])
    page_data = raw_parser.parse_page_html(page.html)
    relevant = []
    for index, block in enumerate(page_data.all_blocks):
        text = block.get("text", "")
        lowered = text.lower()
        if any(token in lowered for token in ("phase", "40%", "70%")):
            relevant.append({"index": index, "type": block.get("type"), "text": text})
    for block in relevant:
        print(f"[{block['index']}] type={block['type']!r} text={block['text']!r}")

    print()
    print("DIRECT EXTRACTOR RESULT")
    direct = extract_phases(page_data.all_blocks)
    for phase in direct:
        print(f"  {phase.label!r} threshold={phase.threshold!r}")


if __name__ == "__main__":
    main()
