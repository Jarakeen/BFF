from __future__ import annotations

import argparse
from pathlib import Path

from engine.config import DEFAULT_DATABASE, get_data_dir
from services.build_service import BuildService
from services.saved_build_capability_service import SavedBuildCapabilityService


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit real saved builds through Phase 5 capability resolution."
    )
    parser.add_argument(
        "--builds",
        type=Path,
        default=get_data_dir() / "builds.json",
        help="Saved Builds compatibility mirror.",
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=DEFAULT_DATABASE,
        help="ESO reference database.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return non-zero when genuine unresolved evidence remains.",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    service = SavedBuildCapabilityService(
        BuildService(args.builds),
        args.database,
    )
    audits = service.audit_roster()

    print("=" * 72)
    print(" PHASE 5 SAVED-BUILD CAPABILITY AUDIT")
    print("=" * 72)
    print(f"Builds:   {args.builds}")
    print(f"Database: {args.database}")
    print(f"Builds audited: {len(audits)}")

    unresolved_total = 0
    for audit in audits:
        print()
        print("-" * 72)
        print(f"{audit.character_name or '(unnamed)'} | {audit.build_name or '(unnamed build)'}")
        print(f"Character ID: {audit.character_id or '(unresolved)'}")
        print(f"Resolved EffectVariants: {len(audit.resolved_effects)}")
        print(
            "Sources: "
            + (", ".join(audit.resolved_sources) if audit.resolved_sources else "(none)")
        )

        if audit.resolved_effects:
            print("Effects:")
            for effect in audit.resolved_effects:
                target = getattr(effect.target_type, "value", effect.target_type) or "self"
                category = getattr(effect.category, "value", effect.category) or "other"
                layer = getattr(effect.layer, "value", effect.layer)
                trigger = f" | trigger={effect.trigger}" if effect.trigger else ""
                condition = f" | condition={effect.condition}" if effect.condition else ""
                print(
                    f"  ✓ {effect.name} | {layer} | {category} | target={target}"
                    f" | source={effect.source}{trigger}{condition}"
                )

        if audit.boundaries:
            print("Intentional boundaries:")
            for message in audit.boundaries:
                print(f"  • {message}")

        if audit.unresolved:
            unresolved_total += len(audit.unresolved)
            print("Unresolved:")
            for message in audit.unresolved:
                print(f"  ⚠ {message}")
        else:
            print("Unresolved: none")

    print()
    print("=" * 72)
    print(f"GENUINE UNRESOLVED ITEMS: {unresolved_total}")
    print("=" * 72)

    if args.strict and unresolved_total:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
