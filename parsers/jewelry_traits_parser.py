# ==================================================
# Black Feather Foundry
#
# File:
# tools/import_jewelry_glyphs.py
#
# ==================================================

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from services.eso_database import EsoDatabase
from importers.jewelry_glyph_importer import (
    JewelryGlyphImporter,
)


DB_PATH = ROOT / "data" / "eso_gear_customization_test.db"

SOURCE_PATH = (
    ROOT
    / "data"
    / "raw"
    / "jewelry_glyph.json"
)


def main():

    db = EsoDatabase(
        str(DB_PATH)
    )

    importer = JewelryGlyphImporter(
        db=db,
        source_path=SOURCE_PATH,
    )

    importer.run()

    db.close()


if __name__ == "__main__":
    main()