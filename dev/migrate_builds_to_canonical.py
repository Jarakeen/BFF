from __future__ import annotations

import argparse
from pathlib import Path

from services.build_catalog_service import BuildCatalogService


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migrate legacy builds.json into canonical character/build catalog data."
    )
    parser.add_argument("--legacy", type=Path, default=Path("data/builds.json"))
    parser.add_argument("--output", type=Path, default=Path("data/characters.json"))
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    service = BuildCatalogService(args.output)
    if args.output.exists() and not args.force:
        raise SystemExit(
            f"Refusing to overwrite existing catalog: {args.output}. Use --force to replace it."
        )

    catalog = service.import_legacy_file(args.legacy)
    service.save(catalog)
    print(
        f"Migrated {len(catalog['builds'])} build(s) across "
        f"{len(catalog['characters'])} character(s) to {args.output}"
    )


if __name__ == "__main__":
    main()
