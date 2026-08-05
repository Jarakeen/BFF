# services/paths.py
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA = PROJECT_ROOT / "data"
ASSETS = PROJECT_ROOT / "assets" 
RAW_DATA = DATA / "raw"
DATABASE = DATA / "database"
EXPORTS = DATA / "exports"
PROCESSED = DATA / "processed"
ICONS = ASSETS / "icons"