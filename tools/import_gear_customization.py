from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.eso_database import EsoDatabase
from importers.gear_customization_importer import (
    GearCustomizationImporter,
)


DB_PATH = ROOT / "data" / "eso_gear_customization_test.db"

RAW_DIR = ROOT / "data" / "raw"


db = EsoDatabase(
    str(DB_PATH)
)
try:

    importer = GearCustomizationImporter(
        db=db,
        raw_dir=RAW_DIR,
    )

    importer.run()

finally:

    db.close()