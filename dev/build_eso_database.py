from pathlib import Path

from services.eso_database import EsoDatabase
from importers.import_eso import EsoImporter

db = EsoDatabase(
    Path("data/db/eso.db")
)

EsoImporter(
    Path("data/raw/"),
    db,
).run()

print("Done.")
