from pathlib import Path

from builders.boss_builder import BossBuilder


builder = BossBuilder(
    raw_folder=Path("data/raw/bosses"),
    output_file=Path("data/processed/bosses.json"),
)

builder.build()