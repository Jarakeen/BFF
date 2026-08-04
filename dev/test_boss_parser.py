from pathlib import Path

from parsers.boss_parser import BossParser

parser = BossParser()

boss = parser.parse(
    Path("data/raw/bahsie.txt")
)

print(boss)
