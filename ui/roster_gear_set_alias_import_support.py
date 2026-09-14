from __future__ import annotations

"""Apply shared gear-set shorthand resolution to roster import and older builds."""

from engine.config import get_data_dir
from services.build_gear_set_alias_backfill_service import backfill_saved_build_gear_aliases
from services.roster_gear_set_alias_service import resolve_roster_gear_set_name


_INSTALLED = False
_ORIGINAL_SLOT_PAYLOAD = None
_ORIGINAL_APPLY_ROSTER_IMPORT = None
LAST_BACKFILL_REPORT = None


def _database_path():
    return get_data_dir() / "eso.db"


def _resolve_set_text(value: object) -> str:
    resolution = resolve_roster_gear_set_name(value, database_path=_database_path())
    return resolution.canonical_name or str(value or "").strip()


def _slot_payload_with_aliases(set_name, weight, trait, enchant, *, weapon: bool = False):
    if not callable(_ORIGINAL_SLOT_PAYLOAD):
        raise RuntimeError("Roster gear alias import bridge is not installed.")
    return _ORIGINAL_SLOT_PAYLOAD(
        _resolve_set_text(set_name),
        weight,
        trait,
        enchant,
        weapon=weapon,
    )


def _normalize_payload_sets(node) -> None:
    """Normalize Set/Set2 fields in JSON-style imported build payloads in place."""
    if isinstance(node, dict):
        for key, value in list(node.items()):
            if key in {"Set", "Set2"} and isinstance(value, str) and value.strip():
                node[key] = _resolve_set_text(value)
            else:
                _normalize_payload_sets(value)
    elif isinstance(node, list):
        for value in node:
            _normalize_payload_sets(value)


def _normalize_plan_payloads(plan) -> None:
    for member in getattr(plan, "members", ()):
        for build in getattr(member, "builds", ()):
            _normalize_payload_sets(getattr(build, "payload", None))


def apply_roster_import_with_set_aliases(plan, roster_service, build_service, *, import_builds: bool = True):
    if not callable(_ORIGINAL_APPLY_ROSTER_IMPORT):
        raise RuntimeError("Roster gear alias import bridge is not installed.")
    _normalize_plan_payloads(plan)
    return _ORIGINAL_APPLY_ROSTER_IMPORT(
        plan,
        roster_service,
        build_service,
        import_builds=import_builds,
    )


def _repair_older_imports() -> None:
    global LAST_BACKFILL_REPORT
    try:
        LAST_BACKFILL_REPORT = backfill_saved_build_gear_aliases(
            get_data_dir() / "builds.json",
            _database_path(),
            create_backup=True,
        )
    except Exception as exc:
        # Import aliases should never make the app fail to start. The repair is
        # intentionally best-effort and can be rerun because it is idempotent.
        print(f"Roster gear alias backfill skipped: {exc}")
        LAST_BACKFILL_REPORT = None


def install() -> None:
    global _INSTALLED, _ORIGINAL_SLOT_PAYLOAD, _ORIGINAL_APPLY_ROSTER_IMPORT
    if _INSTALLED:
        return

    from ui import roster_import_workflow

    _ORIGINAL_SLOT_PAYLOAD = roster_import_workflow._slot_payload
    _ORIGINAL_APPLY_ROSTER_IMPORT = roster_import_workflow.apply_roster_import
    roster_import_workflow._slot_payload = _slot_payload_with_aliases
    roster_import_workflow.apply_roster_import = apply_roster_import_with_set_aliases

    # Repair only recognized old shorthand. Full canonical set names remain
    # untouched, so this does not upgrade deliberately saved non-Perfected gear.
    _repair_older_imports()
    _INSTALLED = True


__all__ = [
    "install",
    "apply_roster_import_with_set_aliases",
    "LAST_BACKFILL_REPORT",
]
