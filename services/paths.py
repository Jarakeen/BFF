# services/paths.py
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Runtime/static application data.
DATA = PROJECT_ROOT / "data"
ASSETS = PROJECT_ROOT / "assets"
USER_DATA = PROJECT_ROOT / "user_data"
MODULES = PROJECT_ROOT / "modules"

# Optional Broadcast module layout.
BROADCAST_MODULE = MODULES / "broadcast"
BROADCAST_RESOURCES = BROADCAST_MODULE / "resources"
BROADCAST_USER_DATA = USER_DATA / "broadcast"

# Developer-only source, evidence, analysis, and generated import material.
# None of these paths should be required by a normal packaged application.
RESEARCH = PROJECT_ROOT / "research"
RAW_DATA = RESEARCH / "raw"
NORMALIZED = RESEARCH / "normalized"
PROCESSED = RESEARCH / "processed"
ESO_INFO = RESEARCH / "eso_info"
ENCOUNTER_EVIDENCE = RESEARCH / "encounter_evidence"
STRATS = RESEARCH / "strats"

DATABASE = DATA / "database"
EXPORTS = DATA / "exports"
ICONS = ASSETS / "icons"
NARRATOR = BROADCAST_RESOURCES / "natural_history_narrator.json"
