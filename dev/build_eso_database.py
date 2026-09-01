from engine.config import DEFAULT_DATABASE
from importers.import_eso import EsoImporter
from services.eso_database import EsoDatabase
from services.paths import RAW_DATA


db = EsoDatabase(DEFAULT_DATABASE)

EsoImporter(
    RAW_DATA,
    db,
).run()

print("Done.")
