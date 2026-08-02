from pathlib import Path

from builders.debuff_builder import DebuffBuilder

DATA_PATH = Path("data/raw")

builder = DebuffBuilder(DATA_PATH)

builder.build()