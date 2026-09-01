import json
from pathlib import Path
from collections import Counter
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.paths import PROCESSED

PATH = PROCESSED / "uesp_collectibles.json"

with PATH.open("r", encoding="utf-8") as f:
    data = json.load(f)

collectibles = data["collectibles"]

category_types = Counter()
category_names = Counter()
subcategory_names = Counter()

missing_type = 0
missing_name = 0
missing_subcategory = 0

for collectible in collectibles:
    fields = collectible.get("fields", {})

    category_type = fields.get("categoryType")
    category_name = fields.get("categoryName")
    subcategory_name = fields.get("subCategoryName")

    if category_type:
        category_types[category_type] += 1
    else:
        missing_type += 1

    if category_name:
        category_names[category_name] += 1
    else:
        missing_name += 1

    if subcategory_name:
        subcategory_names[subcategory_name] += 1
    else:
        missing_subcategory += 1


print("=" * 80)
print("COLLECTIBLE CATEGORIES")
print("=" * 80)

print()
print("CATEGORY TYPE")
print("-" * 80)

for value, count in category_types.most_common():
    print(f"{count:>6,}  {value}")

print()
print("CATEGORY NAME")
print("-" * 80)

for value, count in category_names.most_common():
    print(f"{count:>6,}  {value}")

print()
print("SUBCATEGORY NAME")
print("-" * 80)

for value, count in subcategory_names.most_common():
    print(f"{count:>6,}  {value}")

print()
print("=" * 80)
print(f"TOTAL COLLECTIBLES: {len(collectibles):,}")
print(f"MISSING categoryType: {missing_type:,}")
print(f"MISSING categoryName: {missing_name:,}")
print(f"MISSING subCategoryName: {missing_subcategory:,}")
print("=" * 80)
