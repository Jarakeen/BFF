# dev/run_debuff_builder.py
from pathlib import Path

from builders.debuff_builder import DebuffBuilder
from services.paths import RAW_DATA

DATA_PATH = RAW_DATA / "debuff.txt"

builder = DebuffBuilder(DATA_PATH)

builder.build()