# services/paths.py
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Runtime/static application data.
DATA = PROJECT_ROOT / "data"
ASSETS = PROJECT_ROOT / "assets"

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
NARRATOR = DATA / "Natural_history_narrator.md"
