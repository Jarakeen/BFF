from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.uesp.uesp_client import UespClient


client = UespClient(
    REPO_ROOT / "data" / "uesp" / ".cache"
)

page = client.get_page("Online:Lokkestiiz")

html = page.html

print("HTML LENGTH:", len(html))

needle = "health"
position = html.lower().find(needle)

print("FIRST HEALTH POSITION:", position)

if position >= 0:
    start = max(0, position - 1500)
    end = min(len(html), position + 3000)

    print()
    print("========== RAW HTML AROUND HEALTH ==========")
    print(html[start:end])
else:
    print("No 'health' text found in raw HTML.")