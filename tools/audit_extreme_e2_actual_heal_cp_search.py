from __future__ import annotations

"""Audit E2 legal Champion Point search for Extreme MOST Actual Heal.

This is a read-only integration audit. It loads one real canonical saved build,
discovers every currently reviewed slottable CP star that can affect an actual
healing event, enumerates legal per-discipline bars without comparing mixed units,
and materializes those bars as ordinary BuildCandidates for downstream canonical
heal scoring.
"""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE, get_data_dir
from models.build_model import PlayerBuild
from services.build_catalog_service import BuildCatalogService
from services.extreme_actual_heal_champion_point_candidate_service import (
    ExtremeActualHealChampionPointCandidateService,
)


DEFAULT_CATALOG = get_data_dir() / "characters.json"


def _load_saved_build(
    catalog_path: Path,
    *,
    character: str,
    build_name: str,
) -> tuple[PlayerBuild, str, str]:
    service = BuildCatalogService(catalog_path)
    catalog = service.load()
    matches = [
        row
        for row in catalog.get("characters", ())
        if isinstance(row, dict)
        and str(row.get("name") or "").strip().casefold() == character.casefold()
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Canonical character not found uniquely: {character!r}; matches={len(matches)}"
        )
    character_id = str(matches[0].get("character_id") or "").strip()
    builds = [
        row
        for row in service.builds_for_character(character_id)
        if str(row.get("name") or "").strip().casefold() == build_name.casefold()
    ]
    if len(builds) != 1:
        raise ValueError(
            f"Canonical build not found uniquely: character={character!r} build={build_name!r}; matches={len(builds)}"
        )
    record = builds[0]
    payload = record.get("payload") or record.get("legacy")
    if not isinstance(payload, dict):
        raise ValueError("Canonical build payload is unavailable")
    build_id = str(record.get("build_id") or "").strip()
    if not build_id:
        raise ValueError("Canonical build_id is unavailable")
    return PlayerBuild.from_dict(payload), character_id, build_id


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--character", default="Margrat")
    parser.add_argument("--build", default="DF Healer")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    args = parser.parse_args()

    build, character_id, build_id = _load_saved_build(
        Path(args.catalog),
        character=args.character,
        build_name=args.build,
    )
    service = ExtremeActualHealChampionPointCandidateService(Path(args.database))
    result = service.build_candidates(
        build,
        character_id=character_id,
        baseline_build_id=build_id,
    )

    structurally_legal = True
    candidate_rows = []
    for candidate in result.candidates:
        counts: dict[int, int] = {}
        names: list[str] = []
        for entry in candidate.candidate_build.ChampionPoints:
            name = str(entry.Name or "").strip()
            if not name:
                continue
            record = service.repository.get(name)
            if record is None or record.discipline_index is None:
                structurally_legal = False
                continue
            discipline = int(record.discipline_index)
            counts[discipline] = counts.get(discipline, 0) + 1
            names.append(name)
        if any(count > 4 for count in counts.values()):
            structurally_legal = False
        candidate_rows.append((candidate.candidate_id, tuple(sorted(names)), tuple(sorted(counts.items()))))

    print("EXTREME E2 ACTUAL HEAL CHAMPION POINT SEARCH")
    print(f"database={Path(args.database)}")
    print(f"catalog={Path(args.catalog)}")
    print(f"character={args.character!r}")
    print(f"character_id={character_id!r}")
    print(f"build={args.build!r}")
    print(f"build_id={build_id!r}")
    print()
    print("DISCOVERY")
    print(f"relevant_star_count={len(result.relevant_star_names)}")
    for name in result.relevant_star_names:
        record = service.repository.get(name)
        print(
            f"  relevant: {name} | discipline={getattr(record, 'discipline_index', None)} | max_points={getattr(record, 'max_points', None)}"
        )
    print(f"legal_loadout_count={result.legal_loadout_count}")
    print(f"generated_candidate_count={len(result.candidates)}")
    print()
    print("MATERIALIZED CANDIDATES")
    for candidate_id, names, counts in candidate_rows:
        print(f"  candidate={candidate_id}")
        print(f"    discipline_slot_counts={counts}")
        print(f"    champion_points={names}")
    print()
    print("PROOF STATUS")
    print(f"cp_denominator_proven={result.denominator_proven}")
    print(f"candidate_loadouts_structurally_legal={structurally_legal}")
    print(f"unresolved_count={len(result.unresolved)}")
    for item in result.unresolved:
        print(f"  unresolved: {item}")

    ready = (
        result.denominator_proven
        and structurally_legal
        and result.legal_loadout_count > 0
    )
    print(f"e2_actual_heal_cp_search_ready={ready}")
    if ready:
        print(
            "NEXT_STEP=score the legal CP BuildCandidates through the canonical actual-heal event path; mixed CP units remain intentionally unranked before event evaluation"
        )
    else:
        print(
            "NEXT_STEP=close only the reported heal-relevant CP coverage or structural-legality blockers before claiming this E2 dimension"
        )
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
