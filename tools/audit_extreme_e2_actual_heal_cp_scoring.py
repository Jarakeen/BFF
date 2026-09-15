from __future__ import annotations

"""Score every legal E2 Champion Point loadout through canonical actual-heal math.

This read-only audit is deliberately downstream of CP discovery and structural
legality. ``ExtremeActualHealChampionPointCandidateService`` decides which CP
bars are legal candidates; ``ExtremeCanonicalActualHealOptimizationService``
remains the sole judge of the resulting healing event. Mixed CP units are never
pre-ranked here.
"""

import argparse
from pathlib import Path
import re
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
from services.extreme_canonical_actual_heal_optimization_service import (
    ExtremeCanonicalActualHealOptimizationService,
)
from services.minmax_character_progression_adapter import (
    MinmaxCharacterProgressionAdapter,
)


DEFAULT_CATALOG = get_data_dir() / "characters.json"


def _identity(value: object) -> str:
    text = str(value or "").strip().casefold()
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


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


def _active_bar_for_entity(build: PlayerBuild, entity_id: str) -> str:
    wanted = _identity(entity_id)
    matches: list[str] = []
    for bar, skills in (
        ("front", build.FrontBarSkills),
        ("back", build.BackBarSkills),
    ):
        if any(_identity(skill) == wanted for skill in skills if str(skill or "").strip()):
            matches.append(bar)
    if not matches:
        raise ValueError(
            f"Healing entity is not slotted on the saved build: {entity_id!r}; "
            f"front={tuple(build.FrontBarSkills)!r}; back={tuple(build.BackBarSkills)!r}"
        )
    # If a skill is intentionally double-barred, front is a deterministic witness.
    return "front" if "front" in matches else matches[0]


def _cp_names(build: PlayerBuild) -> tuple[str, ...]:
    return tuple(
        sorted(
            str(entry.Name or "").strip()
            for entry in build.ChampionPoints
            if str(entry.Name or "").strip()
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--character", default="Margrat")
    parser.add_argument("--build", default="DF Healer")
    parser.add_argument("--entity", default="combat_prayer")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    args = parser.parse_args()

    build, character_id, build_id = _load_saved_build(
        Path(args.catalog),
        character=args.character,
        build_name=args.build,
    )
    entity_id = _identity(args.entity)
    active_bar = _active_bar_for_entity(build, entity_id)

    optimizer = ExtremeCanonicalActualHealOptimizationService()
    database_path = Path(args.database)
    if Path(optimizer.optimizer.database_path) != database_path:
        # Keep the audit's explicit database argument authoritative without
        # duplicating the optimizer's context-construction/evaluation pipeline.
        from services.extreme_complete_optimization_service import (
            ExtremeCompleteOptimizationService,
        )

        optimizer = ExtremeCanonicalActualHealOptimizationService(
            optimizer=ExtremeCompleteOptimizationService(database_path=database_path)
        )

    progression_resolution = MinmaxCharacterProgressionAdapter(
        optimizer.optimizer.build_service.canonical.catalog_service
    ).resolve(build)
    progression_unresolved = tuple(progression_resolution.unresolved)
    if not progression_resolution.resolved:
        raise ValueError("; ".join(progression_unresolved))
    if progression_resolution.character_id != character_id:
        raise ValueError(
            "Saved-build progression resolved to a different canonical character: "
            f"catalog={character_id!r} progression={progression_resolution.character_id!r}"
        )

    cp_service = ExtremeActualHealChampionPointCandidateService(database_path)
    candidates = cp_service.build_candidates(
        build,
        character_id=character_id,
        baseline_build_id=build_id,
    )

    cache = {}
    baseline_event, baseline_unresolved = optimizer._evaluate_cached(
        build,
        progression=progression_resolution.progression,
        character_id=character_id,
        build_id=f"{build_id}:e2-cp-score:baseline",
        entity_id=entity_id,
        active_bar=active_bar,
        evaluation_cache=cache,
    )
    if baseline_event.critical_heal is None:
        raise ValueError(
            "Baseline canonical actual-heal event has no critical score: "
            + "; ".join(baseline_event.unresolved)
        )

    scored: list[tuple[float, str, tuple[str, ...], tuple[str, ...]]] = []
    scoring_unresolved: list[str] = list(baseline_unresolved)
    for candidate in candidates.candidates:
        event, unresolved = optimizer._evaluate_cached(
            candidate.candidate_build,
            progression=progression_resolution.progression,
            character_id=character_id,
            build_id=candidate.candidate_id,
            entity_id=entity_id,
            active_bar=active_bar,
            evaluation_cache=cache,
        )
        if event.critical_heal is None:
            scoring_unresolved.append(
                f"{candidate.candidate_id}: canonical critical heal unresolved"
            )
            scoring_unresolved.extend(
                f"{candidate.candidate_id}: {item}" for item in event.unresolved
            )
            continue
        if unresolved:
            scoring_unresolved.extend(
                f"{candidate.candidate_id}: {item}" for item in unresolved
            )
        scored.append(
            (
                float(event.critical_heal),
                candidate.candidate_id,
                _cp_names(candidate.candidate_build),
                tuple(unresolved),
            )
        )

    scored.sort(key=lambda row: (-row[0], row[1]))
    scoring_unresolved = list(dict.fromkeys(item for item in scoring_unresolved if item))
    winner = scored[0] if scored else None

    print("EXTREME E2 ACTUAL HEAL CHAMPION POINT SCORING")
    print(f"database={database_path}")
    print(f"catalog={Path(args.catalog)}")
    print(f"character={args.character!r}")
    print(f"character_id={character_id!r}")
    print(f"build={args.build!r}")
    print(f"build_id={build_id!r}")
    print(f"entity_id={entity_id!r}")
    print(f"active_bar={active_bar!r}")
    print()
    print("BASELINE")
    print(f"baseline_critical_heal={float(baseline_event.critical_heal):.6f}")
    print(f"baseline_champion_points={_cp_names(build)}")
    print(f"baseline_unresolved_count={len(baseline_unresolved)}")
    for item in baseline_unresolved:
        print(f"  baseline_unresolved: {item}")
    print()
    print("LEGAL CP CANDIDATES")
    print(f"legal_loadout_count={candidates.legal_loadout_count}")
    print(f"generated_candidate_count={len(candidates.candidates)}")
    print(f"scored_candidate_count={len(scored)}")
    print(f"cp_denominator_proven={candidates.denominator_proven}")
    print()
    print("TOP SCORES")
    for rank, (score, candidate_id, names, unresolved) in enumerate(scored[:10], start=1):
        print(f"  rank={rank} | critical_heal={score:.6f} | candidate={candidate_id}")
        print(f"    champion_points={names}")
        print(f"    unresolved_count={len(unresolved)}")
    print()
    print("WINNER")
    if winner is None:
        print("winner_candidate=None")
    else:
        winner_score, winner_id, winner_names, winner_unresolved = winner
        print(f"winner_candidate={winner_id}")
        print(f"winner_critical_heal={winner_score:.6f}")
        print(f"winner_gain_over_baseline={winner_score - float(baseline_event.critical_heal):.6f}")
        print(f"winner_champion_points={winner_names}")
        print(f"winner_unresolved_count={len(winner_unresolved)}")
    print()
    print("PROOF STATUS")
    print(f"scoring_unresolved_count={len(scoring_unresolved)}")
    for item in scoring_unresolved:
        print(f"  scoring_unresolved: {item}")

    ready = (
        candidates.denominator_proven
        and candidates.legal_loadout_count > 0
        and len(candidates.candidates) == candidates.legal_loadout_count
        and len(scored) == len(candidates.candidates)
        and not scoring_unresolved
        and winner is not None
    )
    print(f"all_legal_cp_candidates_scored={len(scored) == len(candidates.candidates)}")
    print(f"e2_actual_heal_cp_scoring_ready={ready}")
    if ready:
        print(
            "NEXT_STEP=record Champion Point loadout search as a completed E2 legal-character dimension and proceed to the next missing build dimension"
        )
    else:
        print(
            "NEXT_STEP=close only the reported canonical event-scoring blockers before claiming CP scoring complete"
        )
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
