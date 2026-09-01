"""Backward-compatible entry point for the canonical CP -> skill importer.

The implementation lives in ``importers.champion_point_importer`` so the
crawler/import contract, preserved conditions, and SQLite schema have one
source of truth.
"""

from importers.champion_point_importer import (  # noqa: F401
    ChampionPointSkillImporter,
    DATABASE,
    SOURCE_FILE,
    main,
    normalize_name,
)


if __name__ == "__main__":
    main()
