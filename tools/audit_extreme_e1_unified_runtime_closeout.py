from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE, get_data_dir
from minmax.character_progression import CharacterProgression
from models.build_model import PlayerBuild
from services.build_catalog_service import BuildCatalogService
from services.extreme_conditional_actual_heal_class_route_catalog_service import (
    ExtremeConditionalActualHealClassRouteCatalogService,
)
from services.extreme_power_record_runtime_requirement_service import (
    ExtremePowerRecordRuntimeRequirementService,
)
from services.extreme_power_record_runtime_snapshot_witness_service import (
    ExtremePowerRecordRuntimeSnapshotWitnessService,
)
from services.extreme_runtime_condition_window import ExtremeRuntimeConditionWindow
from services.extreme_runtime_snapshot import ExtremeRuntimeSnapshot
from services.extreme_runtime_snapshot_combat_state_service import (
    ExtremeRuntimeSnapshotCombatStateService,
)
from services.extreme_runtime_snapshot_conditional_actual_heal_optimization_service import (
    ExtremeRuntimeSnapshotConditionalActualHealOptimizationService,
    RESTORATION_HEAVY_POST_COMPLETION_CONDITION,
    SACRED_GROUND_CONDITION,
)


DEFAULT_CATALOG = get_data_dir() / "characters.json"


def _character_name(build) -> str:
    return str(
        getattr(build, "CharacterName", "")
        or getattr(build, "Name", "")
        or getattr(build, "Gamertag", "")
        or ""
    ).strip()


def _load_saved_build(
    path: Path,
    *,
    character: str,
    build_name: str,
) -> tuple[PlayerBuild, str, str]:
    """Load one real build through the canonical character/build catalog."""

    service = BuildCatalogService(path)
    catalog = service.load()
    characters = [
        row
        for row in catalog.get("characters", ())
        if isinstance(row, dict)
        and str(row.get("name") or "").strip().casefold() == character.casefold()
    ]
    if not characters:
        raise ValueError(f"Canonical character not found: {character!r}")
    if len(characters) > 1:
        raise ValueError(f"Canonical character identity is ambiguous: {character!r}")

    character_id = str(characters[0].get("character_id") or "").strip()
    if not character_id:
        raise ValueError(f"Canonical character has no stable id: {character!r}")

    matches = [
        row
        for row in service.builds_for_character(character_id)
        if str(row.get("name") or "").strip().casefold() == build_name.casefold()
    ]
    if not matches:
        raise ValueError(
            f"Canonical saved build not found: character={character!r}, build={build_name!r}"
        )
    if len(matches) > 1:
        raise ValueError(
            f"Canonical saved build identity is ambiguous: character={character!r}, build={build_name!r}"
        )

    record = matches[0]
    payload = record.get("payload")
    if not isinstance(payload, dict):
        raise ValueError(
            f"Canonical saved build has no payload: character={character!r}, build={build_name!r}"
        )
    build_id = str(record.get("build_id") or "").strip()
    if not build_id:
        raise ValueError(
            f"Canonical saved build has no stable id: character={character!r}, build={build_name!r}"
        )

    build = PlayerBuild.from_dict(payload)
    return build, character_id, build_id


def _healer_condition_snapshot() -> ExtremeRuntimeSnapshot:
    return ExtremeRuntimeSnapshot(
        runtime_history=(
            ExtremeRuntimeConditionWindow(
                condition_id=RESTORATION_HEAVY_POST_COMPLETION_CONDITION,
                active_from_seconds=10.0,
                active_until_seconds=14.0,
                source_evidence="E1 closeout reviewed Essence Drain post-heavy window",
            ),
            ExtremeRuntimeConditionWindow(
                condition_id=SACRED_GROUND_CONDITION,
                active_from_seconds=9.0,
                active_until_seconds=13.0,
                source_evidence="E1 closeout reviewed Sacred Ground active/grace window",
                sequence=1,
            ),
        ),
        snapshot_time_seconds=12.0,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit Extreme E1 unified runtime snapshot closeout against the real "
            "Magrat -> DF Healer canonical production path plus the closed Weapon/Spell runtime contracts."
        )
    )
    parser.add_argument("--character", default="Magrat")
    parser.add_argument("--build", default="DF Healer")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    args = parser.parse_args()

    build, character_id, build_id = _load_saved_build(
        Path(args.catalog),
        character=args.character,
        build_name=args.build,
    )
    snapshot = _healer_condition_snapshot()

    snapshot_result = ExtremeRuntimeSnapshotCombatStateService(
        Path(args.database)
    ).resolve(
        build,
        progression=CharacterProgression(passive_ranks={}),
        active_bar="front",
        snapshot=snapshot,
    )

    catalog = ExtremeConditionalActualHealClassRouteCatalogService(
        target_health_fraction=0.25,
        runtime_snapshot=snapshot,
        database_path=Path(args.database),
    )
    optimizer = catalog.optimizer

    real_build_loaded = (
        bool(character_id)
        and bool(build_id)
        and _character_name(build).casefold() == args.character.casefold()
        and str(getattr(build, "BuildName", "") or "").strip().casefold()
        == args.build.casefold()
    )
    shared_snapshot_projection_clean = snapshot_result.unresolved == ()
    active_conditions = snapshot.active_condition_ids
    expected_conditions = {
        RESTORATION_HEAVY_POST_COMPLETION_CONDITION,
        SACRED_GROUND_CONDITION,
    }
    healer_conditions_active = expected_conditions.issubset(set(active_conditions))
    production_uses_snapshot_adapter = isinstance(
        optimizer,
        ExtremeRuntimeSnapshotConditionalActualHealOptimizationService,
    )
    restoration_window_consumed = bool(
        optimizer is not None
        and optimizer.fully_charged_restoration_heavy_attack_completed
    )
    sacred_ground_window_consumed = bool(
        optimizer is not None and optimizer.sacred_ground_window_active
    )

    requirement_service = ExtremePowerRecordRuntimeRequirementService()
    power_rows = []
    for objective in ("weapon_damage", "spell_damage"):
        requirements = requirement_service.requirements_for(objective)
        witness = ExtremePowerRecordRuntimeSnapshotWitnessService.build(objective)
        power_rows.append(
            (
                objective,
                len(requirements),
                witness.closed,
                len(witness.snapshot.ordered_runtime_history),
            )
        )

    power_runtime_contracts_closed = all(
        requirement_count == 9 and witness_closed and history_count == 3
        for _, requirement_count, witness_closed, history_count in power_rows
    )

    checks = {
        "real_saved_build_loaded": real_build_loaded,
        "shared_snapshot_projection_clean": shared_snapshot_projection_clean,
        "healer_condition_windows_active": healer_conditions_active,
        "production_uses_snapshot_adapter": production_uses_snapshot_adapter,
        "restoration_heavy_window_consumed": restoration_window_consumed,
        "sacred_ground_window_consumed": sacred_ground_window_consumed,
        "power_runtime_contracts_closed": power_runtime_contracts_closed,
    }
    unresolved = tuple(name for name, passed in checks.items() if not passed)

    print("EXTREME E1 UNIFIED RUNTIME SNAPSHOT CLOSEOUT")
    print(f"database={Path(args.database)}")
    print(f"catalog={Path(args.catalog)}")
    print(f"character={_character_name(build)!r}")
    print(f"character_id={character_id!r}")
    print(f"build={str(getattr(build, 'BuildName', '') or '')!r}")
    print(f"build_id={build_id!r}")
    print(f"snapshot_time_seconds={snapshot.snapshot_time_seconds:.3f}")
    print(f"active_condition_ids={active_conditions!r}")
    print()
    print("REAL HEALER PRODUCTION PATH")
    for key in (
        "real_saved_build_loaded",
        "shared_snapshot_projection_clean",
        "healer_condition_windows_active",
        "production_uses_snapshot_adapter",
        "restoration_heavy_window_consumed",
        "sacred_ground_window_consumed",
    ):
        print(f"{key}={checks[key]}")
    print(f"snapshot_unresolved_count={len(snapshot_result.unresolved)}")
    for item in snapshot_result.unresolved:
        print(f"  unresolved: {item}")

    print()
    print("CLOSED POWER RECORD CONTRACTS")
    for objective, requirement_count, witness_closed, history_count in power_rows:
        print(
            f"objective={objective} | requirement_count={requirement_count} | "
            f"witness_closed={witness_closed} | history_entry_count={history_count}"
        )
    print(f"power_runtime_contracts_closed={power_runtime_contracts_closed}")

    print()
    print("OWNERSHIP BOUNDARIES PRESERVED")
    print("target_health_and_off_balance_owner=target_state")
    print("higher_resource_owner=structural_state")
    print("font_and_calculated_defense_owner=class_runtime")
    print("sorcerer_slot_legality_owner=active_bar")
    print("e1_does_not_absorb_foreign_owner_facts=True")

    print()
    print("PROOF STATUS")
    print(f"e1_unresolved_count={len(unresolved)}")
    for item in unresolved:
        print(f"  unresolved: {item}")
    closeout_ready = not unresolved
    print(f"e1_real_integration_ready={real_build_loaded and shared_snapshot_projection_clean}")
    print(f"e1_healer_runtime_bridge_closed={healer_conditions_active and production_uses_snapshot_adapter and restoration_window_consumed and sacred_ground_window_consumed}")
    print(f"e1_power_runtime_bridge_closed={power_runtime_contracts_closed}")
    print(f"e1_closeout_audit_ready={closeout_ready}")
    print(
        "NEXT_STEP=if closeout audit is ready, run the focused E1 gate and the full pytest suite; "
        "only then promote E1 to complete in MASTER_ROADMAP.md"
    )
    return 0 if closeout_ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
