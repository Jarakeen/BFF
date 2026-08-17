from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from services.eso_database import EsoDatabase
from importers.armor_glyph_importer import ArmorGlyphImporter


DB_PATH = (
    ROOT
    / "data"
    / "eso_gear_customization_test.db"
)

SOURCE_PATH = (
    ROOT
    / "data"
    / "raw"
    / "armor_glyph.json"
)


def main():

    db = EsoDatabase(
        str(DB_PATH)
    )

    importer = ArmorGlyphImporter(
        db=db,
        source_path=SOURCE_PATH,
    )

    importer.run()

    db.close()


if __name__ == "__main__":
    main()
