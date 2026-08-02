from pathlib import Path

from builders.buff_builder import BuffBuilder

DATA_PATH = Path("data/raw")

builder = BuffBuilder(DATA_PATH)

builder.build()