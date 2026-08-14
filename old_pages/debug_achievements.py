from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.uesp.uesp_client import UespClient
from services.uesp.uesp_parser import parse_page_html


client = UespClient(Path("data/uesp/.cache"))

page = client.get_page("Online:Rockgrove")

parsed = parse_page_html(page.html)

blocks = parsed.sections.get("Achievements", [])

print("ACHIEVEMENT BLOCKS:", len(blocks))

for index, block in enumerate(blocks):
    print(f"\n===== BLOCK {index} =====")
    print(block)