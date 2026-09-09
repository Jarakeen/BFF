from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import get_data_dir, get_resource_path
from services.build_service import BuildService
from services.skill_choice_service import load_skill_choices


def _key(value: str) -> str:
    import re

    return re.sub(r"[^a-z0-9]+", "_", str(value or "").casefold()).strip("_")


def _character_name(build) -> str:
    return str(
        getattr(build, "CharacterName", "")
        or getattr(build, "Name", "")
        or getattr(build, "Gamertag", "")
        or "Unnamed Character"
    ).strip()


def _build_name(build) -> str:
    return str(getattr(build, "BuildName", "") or "Current Build").strip()


def main() -> int:
    icon_root = get_resource_path("assets", "AbilityIcons", "icons", "128")
    database = get_data_dir() / "eso.db"
    builds_path = get_data_dir() / "builds.json"

    print("ROTATION TIMELINE ICON AUDIT")
    print("=" * 72)
    print(f"Icon root:   {icon_root}")
    print(f"Root exists: {icon_root.is_dir()}")
    pngs = tuple(icon_root.glob("*.png")) if icon_root.is_dir() else ()
    print(f"PNG count:   {len(pngs)}")
    print(f"Database:    {database} ({'exists' if database.is_file() else 'MISSING'})")
    print(f"Builds:      {builds_path} ({'exists' if builds_path.is_file() else 'MISSING'})")
    print()

    choices = load_skill_choices(database)
    print(f"Skill choices loaded: {len(choices)}")

    by_alias: dict[str, list[dict]] = {}
    for choice in choices:
        aliases = {
            str(choice.get("name", "") or "").strip().casefold(),
            str(choice.get("index_name", "") or "").strip().casefold(),
            _key(str(choice.get("name", "") or "")),
            _key(str(choice.get("index_name", "") or "")),
        }
        for alias in aliases:
            if alias:
                by_alias.setdefault(alias, []).append(choice)

    if not builds_path.is_file():
        return 1

    roster = BuildService(builds_path).load()
    builds = list(getattr(roster, "Members", ()) or ())
    if not builds:
        print("No saved builds found.")
        return 1

    for build in builds:
        character = _character_name(build)
        build_name = _build_name(build)
        skills: list[tuple[str, int, str]] = []
        for bar_name, values in (
            ("front", getattr(build, "FrontBarSkills", []) or []),
            ("back", getattr(build, "BackBarSkills", []) or []),
        ):
            for slot, raw in enumerate(list(values), start=1):
                name = str(raw or "").strip()
                if name:
                    skills.append((bar_name, slot, name))
        if not skills:
            continue

        print(f"[{character} -> {build_name}]")
        for bar, slot, name in skills:
            matches = []
            seen: set[int] = set()
            for alias in (name.casefold(), _key(name)):
                for choice in by_alias.get(alias, ()):
                    identity = id(choice)
                    if identity not in seen:
                        seen.add(identity)
                        matches.append(choice)

            if not matches:
                print(f"  {bar} {slot}: {name} -> NO DATABASE ALIAS MATCH")
                continue

            choice = matches[0]
            texture = str(choice.get("texture", "") or "").strip()
            filename = Path(texture.replace("\\", "/")).name if texture else ""
            local = icon_root / Path(filename).with_suffix(".png") if filename else None
            exists = bool(local is not None and local.is_file())
            print(
                f"  {bar} {slot}: {name} -> "
                f"db={choice.get('name')!r} index={choice.get('index_name')!r} "
                f"texture={filename or 'NONE'} local={'FOUND' if exists else 'MISSING'}"
            )
            if local is not None:
                print(f"      {local}")
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
