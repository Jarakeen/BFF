from pathlib import Path

from builders.buff_builder import BuffBuilder
from services.paths import RAW_DATA

DATA_PATH = RAW_DATA / "buff.txt"

builder = BuffBuilder(DATA_PATH)


builder.build()