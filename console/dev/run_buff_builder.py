from pathlib import Path

from console.builders.buff_builder import BuffBuilder

DATA_PATH = Path(__file__).parent

builder = BuffBuilder(DATA_PATH)

builder.build()