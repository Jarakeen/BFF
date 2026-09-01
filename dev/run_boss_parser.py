# dev/run_boss_parser.py
from builders.boss_builder import BossBuilder
from services.paths import PROCESSED, RAW_DATA


builder = BossBuilder(
    raw_folder=RAW_DATA / "bosses",
    output_file=PROCESSED / "bosses.json",
)

builder.build()
