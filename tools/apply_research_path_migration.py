from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Replacement:
    path: str
    old: str
    new: str
    expected_count: int = 1


REPLACEMENTS = (
    Replacement(
        "minmax/skill_coefficient_reconciler.py",
        'DEFAULT_DATABASE = Path("data/eso.db")\nDEFAULT_COEFFICIENT_FILE = Path(\n    "data/raw/skill_coef_raw.json"\n)',
        'DEFAULT_DATABASE = Path("data/eso.db")\nDEFAULT_COEFFICIENT_FILE = Path(\n    "research/raw/skill_coef_raw.json"\n)',
    ),
    Replacement(
        "crawlers/eso_hub_skill_cp_crawler.py",
        '- Writes data/raw/skill_champion_points.json.',
        '- Writes research/raw/skill_champion_points.json.',
    ),
    Replacement(
        "crawlers/eso_hub_skill_cp_crawler.py",
        'RAW_DIR = ROOT / "data" / "raw"',
        'RAW_DIR = ROOT / "research" / "raw"',
    ),
    Replacement(
        "crawlers/eso_hub_skill_crawler.py",
        '    data/raw/eso_hub_skill_urls.json',
        '    research/raw/eso_hub_skill_urls.json',
    ),
    Replacement(
        "crawlers/eso_hub_skill_crawler.py",
        '    data/raw/eso_hub_skill_data.json',
        '    research/raw/eso_hub_skill_data.json',
    ),
    Replacement(
        "crawlers/eso_hub_skill_crawler.py",
        '    ROOT\n    / "data"\n    / "raw"\n    / "eso_hub_skill_urls.json"',
        '    ROOT\n    / "research"\n    / "raw"\n    / "eso_hub_skill_urls.json"',
    ),
    Replacement(
        "crawlers/eso_hub_skill_crawler.py",
        '    ROOT\n    / "data"\n    / "raw"\n    / "eso_hub_skill_data.json"',
        '    ROOT\n    / "research"\n    / "raw"\n    / "eso_hub_skill_data.json"',
    ),
    Replacement(
        "crawlers/eso_hub_skill_crawler_v2.py",
        '    data/raw/eso_hub_skill_urls.json',
        '    research/raw/eso_hub_skill_urls.json',
    ),
    Replacement(
        "crawlers/eso_hub_skill_crawler_v2.py",
        '    data/raw/eso_hub_skill_data.json',
        '    research/raw/eso_hub_skill_data.json',
    ),
    Replacement(
        "crawlers/eso_hub_skill_crawler_v2.py",
        '    ROOT\n    / "data"\n    / "raw"\n    / "eso_hub_skill_urls.json"',
        '    ROOT\n    / "research"\n    / "raw"\n    / "eso_hub_skill_urls.json"',
    ),
    Replacement(
        "crawlers/eso_hub_skill_crawler_v2.py",
        '    ROOT\n    / "data"\n    / "raw"\n    / "eso_hub_skill_data.json"',
        '    ROOT\n    / "research"\n    / "raw"\n    / "eso_hub_skill_data.json"',
    ),
    Replacement(
        "services/esologs_json_adapter.py",
        '(e.g. data/raw/esologs_night2.json)',
        '(e.g. research/raw/esologs_night2.json)',
    ),
    Replacement(
        "services/esologs_json_adapter.py",
        'DEFAULT_RAW_PATH = Path("data/raw/esologs_night2.json")',
        'DEFAULT_RAW_PATH = Path("research/raw/esologs_night2.json")',
    ),
    Replacement(
        "tests/normalize_reagents.py",
        'Put the actual reagent JSON in data/raw and rerun.',
        'Put the actual reagent JSON in research/raw and rerun.',
    ),
    Replacement(
        "ui/desktop_gui.py",
        'then dive into data/processed/',
        'then use the canonical processed research directory',
    ),
)


def grouped_replacements() -> dict[str, list[Replacement]]:
    result: dict[str, list[Replacement]] = {}
    for replacement in REPLACEMENTS:
        result.setdefault(replacement.path, []).append(replacement)
    return result


def inspect_file(path: Path, replacements: list[Replacement]) -> list[str]:
    errors: list[str] = []
    if not path.exists():
        return [f"missing file: {path.relative_to(ROOT)}"]

    text = path.read_text(encoding="utf-8")
    for replacement in replacements:
        count = text.count(replacement.old)
        if count != replacement.expected_count:
            errors.append(
                f"{replacement.path}: expected {replacement.expected_count} occurrence(s), found {count}: {replacement.old!r}"
            )
    return errors


def apply_file(path: Path, replacements: list[Replacement]) -> None:
    text = path.read_text(encoding="utf-8")
    for replacement in replacements:
        text = text.replace(replacement.old, replacement.new, replacement.expected_count)
    path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Guarded one-time patch for the research/raw path migration."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply replacements. Without this flag the tool is read-only.",
    )
    args = parser.parse_args()

    grouped = grouped_replacements()
    errors: list[str] = []
    for relative, replacements in grouped.items():
        errors.extend(inspect_file(ROOT / relative, replacements))

    print("=" * 72)
    print(" RESEARCH PATH MIGRATION PATCHER")
    print("=" * 72)
    print(f"mode: {'APPLY' if args.apply else 'DRY RUN'}")
    print(f"files: {len(grouped)}")
    print(f"replacements: {len(REPLACEMENTS)}")
    print()

    if errors:
        print("REFUSED: checkout does not match the expected source text.")
        for error in errors:
            print(f"  - {error}")
        print("No files were changed.")
        return 1

    if not args.apply:
        print("All expected legacy declarations are present exactly once.")
        print("No files were changed. Run again with --apply to patch them.")
        return 0

    for relative, replacements in grouped.items():
        apply_file(ROOT / relative, replacements)
        print(f"updated: {relative}")

    print()
    print("Migration path declarations updated.")
    print("No data files or database rows were changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
