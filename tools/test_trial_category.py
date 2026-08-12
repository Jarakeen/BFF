from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.uesp.uesp_client import UespClient


CACHE = REPO_ROOT / "data" / "uesp" / ".cache"

client = UespClient(
    cache_dir=CACHE,
    min_request_interval=2.0,
)

print("Checking UESP category: Online-Trials")
print()

titles = client.get_category_members("Online-Trials")

print(f"FOUND: {len(titles)} pages")
print()

for title in titles:
    print(title)