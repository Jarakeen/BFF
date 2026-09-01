from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from crawlers.eso_hub_skill_cp_crawler import (
    BASE_URL,
    INDEX_URL,
    choose_skill_url,
    discover_skill_urls,
    extract_cp_section,
    fetch_html,
    load_champion_points,
    load_skills,
    normalize_name,
)
from engine.config import get_data_dir
from importers.champion_point_importer import ChampionPointSkillImporter
from models.build_model import PlayerBuild

try:
    from bs4 import BeautifulSoup
except ImportError as exc:  # pragma: no cover - dependency error is user-facing
    raise SystemExit(
        "beautifulsoup4 is required. Install project crawler dependencies first."
    ) from exc


DEFAULT_BUILDS = get_data_dir() / "builds.json"
DEFAULT_OUTPUT_DIR = get_data_dir() / "raw"


def _load_saved_build(path: Path, requested: str) -> PlayerBuild:
    payload = json.loads(path.read_text(encoding="utf-8"))
    members = payload.get("Members") if isinstance(payload, dict) else None
    if not isinstance(members, list):
        raise ValueError(f"Unsupported saved-build format in {path}; expected Members")

    key = str(requested or "").strip().casefold()
    matches = [
        PlayerBuild.from_dict(entry)
        for entry in members
        if isinstance(entry, dict)
        and str(entry.get("BuildName", "")).strip().casefold() == key
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Expected exactly one saved build named {requested!r}; found {len(matches)}"
        )
    return matches[0]


def _saved_skill_names(saved: PlayerBuild) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in tuple(saved.FrontBarSkills) + tuple(saved.BackBarSkills):
        name = str(value or "").strip()
        key = normalize_name(name)
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(name)
    return tuple(result)


def _output_path(build_name: str, output_dir: Path) -> Path:
    slug = normalize_name(build_name).replace(" ", "_") or "saved_build"
    return output_dir / f"skill_champion_points.partial.{slug}.json"


def _db_skill_lookup() -> dict[str, list[dict]]:
    result: dict[str, list[dict]] = {}
    for skill in load_skills():
        for candidate in (skill.get("name"), skill.get("index_name")):
            key = normalize_name(str(candidate or ""))
            if key:
                result.setdefault(key, []).append(skill)
    return result


def recover(
    *,
    builds_path: Path,
    build_name: str,
    output_dir: Path,
    import_relationships: bool,
) -> int:
    if not builds_path.exists():
        print(f"Saved builds not found: {builds_path}")
        return 1

    try:
        saved = _load_saved_build(builds_path, build_name)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(exc)
        return 2

    requested_names = _saved_skill_names(saved)
    if not requested_names:
        print(f"Saved build has no slotted skills: {build_name}")
        return 3

    cp_vocab = load_champion_points()
    skill_lookup = _db_skill_lookup()
    urls = discover_skill_urls()

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = _output_path(build_name, output_dir)

    print()
    print("========================================")
    print(" PHASE 5 TARGETED CP -> SKILL RECOVERY")
    print("========================================")
    print(f"Character:    {saved.Name or '(unnamed)'}")
    print(f"Build:        {saved.BuildName or '(unnamed)'}")
    print(f"Saved skills: {len(requested_names)}")
    print(f"CP vocabulary:{len(cp_vocab):>5}")
    print(f"Output:       {output_path}")
    print()

    records: list[dict] = []
    failures: list[str] = []

    for number, saved_name in enumerate(requested_names, start=1):
        matches = skill_lookup.get(normalize_name(saved_name), [])
        if len(matches) != 1:
            label = "not found in skill table" if not matches else f"ambiguous ({len(matches)} matches)"
            print(f"[{number}/{len(requested_names)}] {saved_name} -> {label}")
            failures.append(f"{saved_name}: {label}")
            continue

        skill = matches[0]
        match = choose_skill_url(skill, urls)
        if match is None:
            print(f"[{number}/{len(requested_names)}] {saved_name} -> no unique ESO-Hub URL")
            failures.append(f"{saved_name}: no unique ESO-Hub URL")
            continue

        url = str(match["url"])
        print(f"[{number}/{len(requested_names)}] {saved_name} -> {url}")
        html = fetch_html(url)
        if not html:
            failures.append(f"{saved_name}: page fetch failed")
            continue

        cp_entries, error = extract_cp_section(
            BeautifulSoup(html, "html.parser"),
            str(skill["name"]),
            cp_vocab,
        )
        record = {
            "skill_id": skill["id"],
            "skill_name": skill["name"],
            "skill_base_ability_id": skill["base_ability_id"],
            "skill_line": skill["skill_line"],
            "url": url,
            "champion_points": cp_entries,
            "parse_status": error or ("ok" if cp_entries else "section_found_but_no_cp_matches"),
        }
        records.append(record)

        payload = {
            "source": "ESO-Hub",
            "source_index": INDEX_URL,
            "generated_by": "recover_saved_build_cp_skill_evidence.py",
            "scope": "partial_saved_build",
            "build_name": saved.BuildName,
            "character_name": saved.Name,
            "complete_corpus": False,
            "skills": records,
        }
        output_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    if not records:
        print()
        print("No ESO-Hub skill records were recovered.")
        for failure in failures:
            print(f"  - {failure}")
        return 4

    payload = {
        "source": "ESO-Hub",
        "source_index": INDEX_URL,
        "generated_by": "recover_saved_build_cp_skill_evidence.py",
        "scope": "partial_saved_build",
        "build_name": saved.BuildName,
        "character_name": saved.Name,
        "complete_corpus": False,
        "skills": records,
    }
    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    cp_links = sum(len(record["champion_points"]) for record in records)
    print()
    print(f"Recovered skill records: {len(records)}")
    print(f"Recovered CP links:      {cp_links}")
    print(f"Failures:                {len(failures)}")
    for failure in failures:
        print(f"  - {failure}")

    if import_relationships:
        print()
        print("Importing recovered explicit relationships into champion_point_skill...")
        ChampionPointSkillImporter(source_file=output_path).run()
    else:
        print()
        print("Read-only recovery complete. Database was not changed.")
        print("Rerun with --import after inspecting the partial evidence file.")

    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Recover ESO-Hub CP -> skill evidence only for skills slotted on one saved build. "
            "The output is explicitly marked partial and never replaces a full harvest."
        )
    )
    parser.add_argument("--builds", type=Path, default=DEFAULT_BUILDS)
    parser.add_argument("--build", default="DF Healer")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--import",
        dest="import_relationships",
        action="store_true",
        help="Import recovered explicit links into champion_point_skill after writing the partial evidence file.",
    )
    return parser


if __name__ == "__main__":
    args = _parser().parse_args()
    raise SystemExit(
        recover(
            builds_path=args.builds,
            build_name=args.build,
            output_dir=args.output_dir,
            import_relationships=args.import_relationships,
        )
    )
