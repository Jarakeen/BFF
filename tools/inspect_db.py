import sqlite3 
import pathlib
from services.settings_service import SettingsService
from services.esologs_client import EsoLogsClient
settings = SettingsService(Path("settings.json")).load()

client = EsoLogsClient(
    client_id=settings.get("EsoLogsClientId", ""),
    client_secret=settings.get("EsoLogsClientSecret", ""),
)
db = sqlite3.connect("data/eso.db")

rows = db.execute(
    "SELECT name FROM sqlite_master "
    "WHERE type = 'table' "
    "ORDER BY name"
).fetchall()

for row in rows:
    print(row[0])

db.close()
