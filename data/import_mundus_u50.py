from __future__ import annotations

import argparse
from pathlib import Path

from minmax.mundus_repository import MundusRepository, U50_GAME_UPDATE


def main() -> None:
    parser = argparse.ArgumentParser(description="Create and seed the canonical Update 50 Mundus tables.")
    parser.add_argument("database", nargs="?", default=str(Path(__file__).with_name("eso.db")))
    args = parser.parse_args()

    repository = MundusRepository(args.database, game_update=U50_GAME_UPDATE)
    names = repository.list_names()
    print(f"Imported {len(names)} Update {U50_GAME_UPDATE} Mundus Stones into {args.database}")


if __name__ == "__main__":
    main()
