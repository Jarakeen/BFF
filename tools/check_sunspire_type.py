from pathlib import Path

from services.uesp.uesp_client import UespClient
from services.uesp.uesp_parser import UespParser

client = UespClient(
    cache_dir=Path("data/uesp/.cache")
)

page = client.get_page("Online:Sunspire")

print("=== SUNSPIRE CATEGORIES ===")
for category in page.categories:
    print(category)

print()
print("=== DETECTED CONTENT TYPE ===")

parser = UespParser()
print(parser.detect_content_type(page, default="dungeon"))
