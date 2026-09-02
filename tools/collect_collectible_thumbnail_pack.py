from __future__ import annotations

import argparse
from pathlib import Path

from services.content_packs import COLLECTIBLE_ICONS_PACK
from tools.collect_collectible_icons import DEFAULT_DATA_DIR, collect


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the optional collectible thumbnail content pack."
    )
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument(
        "--html-dir",
        type=Path,
        default=None,
        help="Root containing saved .html/.htm pages. Defaults to data-dir.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=COLLECTIBLE_ICONS_PACK,
        help="Optional pack destination. Defaults to content_packs/collectible_icons.",
    )
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--no-download", action="store_true")
    args = parser.parse_args()

    data_dir = args.data_dir.resolve()
    html_dir = (args.html_dir or data_dir).resolve()
    output_dir = args.output_dir.resolve()

    print("=" * 64)
    print(" BFF OPTIONAL COLLECTIBLE THUMBNAIL PACK")
    print("=" * 64)
    print(f"Data:       {data_dir}")
    print(f"Saved HTML: {html_dir}")
    print(f"Pack:       {output_dir}")
    print()

    collect(
        data_dir=data_dir,
        html_dir=html_dir,
        output_dir=output_dir,
        force=args.force,
        no_download=args.no_download,
    )


if __name__ == "__main__":
    main()
