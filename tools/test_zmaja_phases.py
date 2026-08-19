from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.uesp.uesp_client import UespClient
from services.uesp.uesp_parser import UespParser, parse_page_html


client = UespClient(
    REPO_ROOT / "data" / "uesp" / ".cache"
)

page = client.get_page("Online:Z'Maja")

parsed = parse_page_html(page.html)

print("TITLE:", page.title)

print()
print("========== SECTIONS ==========")

for heading, blocks in parsed.sections.items():
    print()
    print(f"### {heading}")

    for block in blocks:
        print(block)

parser = UespParser()

boss = parser.parse_boss(
    page,
    content_id="cloudrest",
    content_name="Cloudrest",
)

print()
print("========== PHASES ==========")

for phase in boss.phases:
    print("LABEL:", phase.label)
    print("THRESHOLD:", phase.threshold)
    print("DESCRIPTION:", phase.description)
    print()
