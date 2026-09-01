from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from crawlers.eso_hub_cp_section_parser import extract_current_cp_section
from crawlers.eso_hub_skill_cp_crawler import (
    BASE_URL,
    INDEX_URL,
    choose_skill_url,
    discover_skill_urls,
    fetch_html,
    load_champion_points,
    load_skills,
    normalize_name,
    normalize_text,
    slugify_name,
)
from engine.config import DEFAULT_DATABASE, get_data_dir
from importers.champion_point_importer import ChampionPointSkillImporter
from minmax.skill_coefficient_repository import SkillCoefficientRepository
from models.build_model import PlayerBuild

try:
    from bs4 import BeautifulSoup
except ImportError as exc:  # pragma: no cover
    raise SystemExit("beautifulsoup4 is required. Install project crawler dependencies first.") from exc


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
        raise ValueError(f"Expected exactly one saved build named {requested!r}; found {len(matches)}")
    return matches[0]


def _saved_skill_names(saved: PlayerBuild) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in tuple(saved.FrontBarSkills) + tuple(saved.BackBarSkills):
        name = str(value or "").strip()
        key = normalize_name(name)
        if key and key not in seen:
            seen.add(key)
            result.append(name)
    return tuple(result)


def _output_path(build_name: str, output_dir: Path) -> Path:
    slug = normalize_name(build_name).replace(" ", "_") or "saved_build"
    return output_dir / f"skill_champion_points.partial.{slug}.json"


def _base_skills_by_id() -> dict[int, dict]:
    return {int(skill["id"]): skill for skill in load_skills()}


def _links_from_page(url: str) -> list[dict]:
    html = fetch_html(url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    found: dict[str, dict] = {}
    for anchor in soup.find_all("a", href=True):
        absolute = urljoin(BASE_URL, anchor.get("href", ""))
        if not absolute.startswith(BASE_URL + "/en/skills/"):
            continue
        parsed = urlparse(absolute)
        clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if clean.rstrip("/") == url.rstrip("/"):
            continue
        text = normalize_text(anchor.get_text(" ", strip=True))
        found.setdefault(
            clean,
            {
                "url": clean,
                "anchor_text": text,
                "slug": parsed.path.rstrip("/").split("/")[-1],
            },
        )
    return list(found.values())


def _urls_for_skill_line(skill: dict, index_urls: list[dict], cache: dict[str, list[dict]]) -> list[dict]:
    line = str(skill.get("skill_line") or "").strip()
    key = normalize_name(line)
    if not key:
        return index_urls
    if key in cache:
        return cache[key]

    line_slug = slugify_name(line)
    candidates = [item for item in index_urls if str(item.get("slug") or "").casefold() == line_slug.casefold()]
    if len(candidates) != 1:
        candidates = [
            item
            for item in index_urls
            if normalize_name(str(item.get("anchor_text") or "")) == key
        ]
    if len(candidates) == 1:
        children = _links_from_page(str(candidates[0]["url"]))
        cache[key] = children or index_urls
    else:
        cache[key] = index_urls
    return cache[key]


def _verified_class_skill_url(skill: dict, rank_name: str) -> str | None:
    class_name = str(skill.get("class_type") or "").strip()
    skill_line = str(skill.get("skill_line") or "").strip()
    if not class_name or not skill_line:
        return None

    candidate = (
        f"{BASE_URL}/en/skills/{slugify_name(class_name)}/"
        f"{slugify_name(skill_line)}/{slugify_name(rank_name)}"
    )
    html = fetch_html(candidate)
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")
    expected = normalize_name(rank_name)
    h1 = soup.find("h1")
    if h1 is None:
        return None
    heading = normalize_name(h1.get_text(" ", strip=True))
    if heading == expected or heading.startswith(expected + " skill"):
        return candidate
    return None


def recover(
    *,
    database_path: Path,
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
    base_skills = _base_skills_by_id()
    coefficient_repository = SkillCoefficientRepository(database_path)
    index_urls = discover_skill_urls()
    line_url_cache: dict[str, list[dict]] = {}

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
        resolution = coefficient_repository.resolve_name(saved_name)
        if resolution.rank is None:
            reason = "; ".join(resolution.unresolved) or "canonical skill resolution failed"
            print(f"[{number}/{len(requested_names)}] {saved_name} -> {reason}")
            failures.append(f"{saved_name}: {reason}")
            continue

        rank = resolution.rank
        base = base_skills.get(rank.skill_id)
        if base is None:
            label = f"base skill id {rank.skill_id} not found"
            print(f"[{number}/{len(requested_names)}] {saved_name} -> {label}")
            failures.append(f"{saved_name}: {label}")
            continue

        skill = dict(base)
        skill["name"] = rank.name
        urls = _urls_for_skill_line(skill, index_urls, line_url_cache)
        match = choose_skill_url(skill, urls)
        url = str(match["url"]) if match is not None else _verified_class_skill_url(skill, rank.name)
        if not url:
            print(f"[{number}/{len(requested_names)}] {saved_name} -> no verified ESO-Hub URL")
            failures.append(f"{saved_name}: no verified ESO-Hub URL")
            continue

        print(f"[{number}/{len(requested_names)}] {saved_name} -> {url}")
        html = fetch_html(url)
        if not html:
            failures.append(f"{saved_name}: page fetch failed")
            continue

        cp_entries, error = extract_current_cp_section(
            BeautifulSoup(html, "html.parser"),
            rank.name,
            cp_vocab,
        )
        record = {
            "skill_id": rank.skill_id,
            "skill_rank_id": rank.skill_rank_id,
            "ability_id": rank.ability_id,
            "skill_name": rank.name,
            "skill_base_ability_id": rank.base_ability_id,
            "skill_line": base.get("skill_line"),
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
        output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    if not records:
        print()
        print("No ESO-Hub skill records were recovered.")
        for failure in failures:
            print(f"  - {failure}")
        return 4

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
        ChampionPointSkillImporter(database=database_path, source_file=output_path).run()
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
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--builds", type=Path, default=DEFAULT_BUILDS)
    parser.add_argument("--build", default="DF Healer")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--import", dest="import_relationships", action="store_true")
    return parser


if __name__ == "__main__":
    args = _parser().parse_args()
    raise SystemExit(
        recover(
            database_path=args.database,
            builds_path=args.builds,
            build_name=args.build,
            output_dir=args.output_dir,
            import_relationships=args.import_relationships,
        )
    )
