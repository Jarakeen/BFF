from pathlib import Path

from console.builders.debuff_builder import DebuffBuilder

DATA_PATH = Path(__file__).parent

builder = DebuffBuilder(DATA_PATH)

builder.build()