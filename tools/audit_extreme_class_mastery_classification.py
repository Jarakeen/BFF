from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.config import get_data_dir
from services.class_mastery_classification_service import ClassMasteryClassificationService
from services.class_mastery_repository import ClassMasteryRepository


def main() -> int:
    database = get_data_dir() / "eso.db"
    repository = ClassMasteryRepository(database)
    rows = ClassMasteryClassificationService.classify_all(repository.all())

    print("=" * 112)
    print(" EXTREME BUILD CLASS MASTERY CLASSIFICATION AUDIT")
    print("=" * 112)
    print(f"Database: {database}")
    print(f"Canonical Class Mastery passives: {len(rows)}")
    print("Boundary only: this audit does not grant numeric stats or claim an Extreme Build winner.")
    print()

    counts = Counter(row.boundary.value for row in rows)
    for boundary in sorted(counts):
        print(f"{boundary:30s} {counts[boundary]:2d}")

    print()
    print("class | passive | boundary | relevant Extreme objectives")
    print("-" * 112)
    for row in rows:
        objectives = ", ".join(row.objective_keys) or "none"
        print(
            f"{row.passive.class_name:12s} | {row.passive.name:28.28s} | "
            f"{row.boundary.value:29s} | {objectives}"
        )

    print()
    print("Optimizer rule: only reviewed numeric effect mappings may alter a score. Classification alone is not stat math.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
