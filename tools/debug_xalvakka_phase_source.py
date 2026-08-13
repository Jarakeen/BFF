from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.uesp.uesp_client import UespClient
from services.uesp.uesp_parser import parse_page_html

CACHE = REPO_ROOT / "data" / "uesp" / ".cache"


def main() -> None:
    page = UespClient(CACHE).get_page("Online:Xalvakka")
    parsed = parse_page_html(page.html)
    print("XALVAKKA PHASE SOURCE DIAGNOSTIC")
    for i, block in enumerate(parsed.all_blocks):
        text = block.get("text", "")
        lower = text.lower()
        if "phase" in lower or "40%" in text or "40 %" in text:
            print(f"[{i}] type={block.get('type')!r} text={text!r}")


if __name__ == "__main__":
    main()
