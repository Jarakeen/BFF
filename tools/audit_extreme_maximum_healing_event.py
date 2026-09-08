from __future__ import annotations

"""Read-only audit for the unified Extreme maximum single-healing-event objective."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE, get_data_dir
from models.build_model import PlayerBuild
from services.build_service import BuildService
from services.extreme_actual_heal_class_route_catalog_service import (
    ExtremeActualHealClassRouteCatalogService,
)
from services.extreme_maximum_healing_event_class_route_catalog_service import (
    ExtremeMaximumHealingEventClassRouteCatalogService,
)
from services.extreme_sorcerer_blood_magic_class_route_catalog_service import (
    ExtremeSorcererBloodMagicClassRouteCatalogService,
)

DEFAULT_BUILDS = get_data_dir() / "builds.json"


def _find_build(builds: tuple[PlayerBuild, ...] | list[PlayerBuild], requested: str) -> PlayerBuild:
    key = str(requested or "").strip().casefold()
    matches = [
        build
        for build in builds
        if str(build.BuildName or "").strip().casefold() == key
    ]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ValueError(f"Ambiguous build name: {requested!r}")
    raise ValueError(f"Saved build not found: {requested!r}")


def _join(values) -> str:
    items = tuple(str(value) for value in tuple(values or ()) if str(value).strip())
    return ", ".join(items) if items else "(none)"


def _format_entry(entry, *, index: int) -> list[str]:
    value = "UNKNOWN" if entry.event_value is None else f"{float(entry.event_value):.3f}"
    route = _join(getattr(entry.route, "equipped_skill_lines", ()))
    status = "complete" if entry.mechanic_complete else "incomplete"
    lines = [
        f"[{index:02d}] {entry.source_name}",
        f"     source: {entry.source_kind}",
        f"     maximum event: {value} ({entry.event_kind})",
        f"     route: {route}",
        f"     active-bar slot: {int(entry.slotted_index) + 1}",
        f"     evidence: {status}",
    ]
    trace = entry.trace
    if trace.coefficient_numbers:
        lines.append("     winning coefficients: " + _join(trace.coefficient_numbers))
    if trace.recipient_scopes or trace.recipient_keys:
        lines.append(
            "     recipient: "
            + _join(trace.recipient_scopes)
            + " / "
            + _join(trace.recipient_keys)
        )
    if trace.event_keys:
        lines.append("     event identity: " + _join(trace.event_keys))
    if trace.temporal_scopes:
        lines.append("     timing: " + _join(trace.temporal_scopes))
    unresolved = tuple(dict.fromkeys((*tuple(entry.unresolved), *tuple(trace.unresolved))))
    for message in unresolved:
        lines.append(f"     unresolved: {message}")
    return lines


def format_report(result, *, build: PlayerBuild, active_bar: str, top: int = 10) -> str:
    lines = [
        "====================================================",
        " EXTREME MAXIMUM SINGLE HEALING EVENT AUDIT",
        "====================================================",
        f"Character: {build.Name or '(unnamed)'}",
        f"Build: {build.BuildName or '(unnamed)'}",
        f"Base class: {build.EsoClass or '(unknown)'}",
        f"Active bar: {active_bar}",
        "Objective: largest legal single healing event to one canonical recipient/event identity",
        "Boundary: read-only; not HPS, healing per cast, or expected healing",
        "",
    ]

    explanation = result.winner_explanation
    if explanation is None:
        lines.extend(
            [
                "WINNER",
                "  No candidate has a proved maximum-event value.",
            ]
        )
    else:
        lines.extend(
            [
                "WINNER",
                f"  {explanation.source_name}",
                f"  Maximum event: {explanation.event_value:.3f} ({explanation.event_kind})",
                f"  Source: {explanation.source_kind}",
                f"  Route: {_join(explanation.route_skill_lines)}",
                f"  Active-bar slot: {int(explanation.slotted_index) + 1}",
                f"  Recipient: {_join(explanation.trace.recipient_scopes)} / {_join(explanation.trace.recipient_keys)}",
                f"  Event identity: {_join(explanation.trace.event_keys)}",
                f"  Timing: {_join(explanation.trace.temporal_scopes)}",
                f"  Winning coefficients: {_join(explanation.trace.coefficient_numbers)}",
                f"  Runner-up: {explanation.runner_up_name or '(none)'}",
                "  Margin: " + ("(none)" if explanation.margin is None else f"{explanation.margin:.3f}"),
                f"  Why: {explanation.reason}",
            ]
        )

    lines.extend(
        [
            "",
            "PROOF STATUS",
            f"  Global maximum proven: {'YES' if result.global_maximum_proven else 'NO'}",
            f"  Scored entries: {sum(1 for entry in result.entries if entry.event_value is not None)}",
            f"  Total entries: {len(result.entries)}",
        ]
    )

    if result.omitted_scope:
        lines.append("  Remaining omitted scope:")
        lines.extend(f"    - {item}" for item in result.omitted_scope)
    else:
        lines.append("  Remaining omitted scope: none")

    lines.extend(["", "TOP CANDIDATES"])
    shown = tuple(result.entries[: max(0, int(top))])
    if not shown:
        lines.append("  (none)")
    else:
        for index, entry in enumerate(shown, 1):
            lines.extend(_format_entry(entry, index=index))

    lines.extend(["", "SEARCH SCOPE"])
    lines.extend(f"  - {item}" for item in result.search_scope)
    return "\n".join(lines)


def audit(
    *,
    build_name: str,
    database_path: Path,
    builds_path: Path,
    active_bar: str,
    max_passes: int,
    include_base_class_changes: bool,
    top: int,
) -> int:
    if not database_path.exists():
        print(f"Database not found: {database_path}")
        return 1
    if not builds_path.exists():
        print(f"Build file not found: {builds_path}")
        return 1

    try:
        build = _find_build(tuple(BuildService(builds_path).load().Members), build_name)
    except ValueError as exc:
        print(str(exc))
        return 2

    ordinary = ExtremeActualHealClassRouteCatalogService(database_path=database_path)
    blood_magic = ExtremeSorcererBloodMagicClassRouteCatalogService(database_path=database_path)
    service = ExtremeMaximumHealingEventClassRouteCatalogService(
        ordinary=ordinary,
        blood_magic=blood_magic,
    )
    result = service.rank(
        build,
        active_bar=active_bar,
        max_passes=max_passes,
        include_base_class_changes=include_base_class_changes,
    )
    print(format_report(result, build=build, active_bar=active_bar, top=top))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", required=True, help="Saved BuildName to audit")
    parser.add_argument(
        "--database",
        type=Path,
        default=Path(DEFAULT_DATABASE),
        help="Path to eso.db (default: canonical data/eso.db)",
    )
    parser.add_argument(
        "--builds",
        type=Path,
        default=Path(DEFAULT_BUILDS),
        help="Path to builds.json",
    )
    parser.add_argument("--active-bar", choices=("front", "back"), default="front")
    parser.add_argument("--max-passes", type=int, default=24)
    parser.add_argument("--include-base-class-changes", action="store_true")
    parser.add_argument("--top", type=int, default=10)
    args = parser.parse_args()
    return audit(
        build_name=args.build,
        database_path=args.database,
        builds_path=args.builds,
        active_bar=args.active_bar,
        max_passes=args.max_passes,
        include_base_class_changes=args.include_base_class_changes,
        top=args.top,
    )


if __name__ == "__main__":
    raise SystemExit(main())
