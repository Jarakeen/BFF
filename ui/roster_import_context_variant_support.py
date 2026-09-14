from __future__ import annotations

"""Make roster re-imports replace prior team imports and fold loadouts into variants.

A repeated import for one team/player should replace the builds previously imported
for that same team/player, not accumulate another pile of full-build clones.  One
reviewed base loadout remains a normal saved build; boss-specific alternates become
sparse Team + Boss Context Variants when that conversion is lossless.
"""

from copy import deepcopy
from pathlib import Path
import shutil

from engine.config import get_data_dir
from models.build_model import BuildRoster
from services.roster_import_context_variant_service import consolidate_member_builds


_INSTALLED = False
_ORIGINAL_APPLY_ROSTER_IMPORT = None
_ORIGINAL_RESOLVE_IMPORT_CHARACTERS = None


def _identity_key(value: object) -> str:
    return " ".join(str(value or "").strip().split()).lstrip("@").casefold()


def _personnel_character_candidates(roster_service, member) -> list[str]:
    wanted_player = _identity_key(getattr(member, "gamertag", ""))
    wanted_class = str(getattr(member, "eso_class", "") or "").strip().casefold()
    result: list[str] = []
    for existing in roster_service.list_members():
        if _identity_key(getattr(existing, "PlayerName", "")) != wanted_player:
            continue
        name = str(getattr(existing, "CharacterName", "") or "").strip()
        if not name:
            continue
        existing_class = str(getattr(existing, "EsoClass", "") or "").strip().casefold()
        if wanted_class and existing_class and existing_class != wanted_class:
            continue
        if name.casefold() not in {value.casefold() for value in result}:
            result.append(name)
    return result


def resolve_import_characters_with_personnel_priority(plan, roster_service, build_service) -> None:
    """Prefer the one current Personnel character before historical catalog extras."""
    if not callable(_ORIGINAL_RESOLVE_IMPORT_CHARACTERS):
        raise RuntimeError("Roster context-variant import bridge is not installed.")

    for member in getattr(plan, "members", ()):
        if str(getattr(member, "character_name", "") or "").strip():
            continue
        candidates = _personnel_character_candidates(roster_service, member)
        if len(candidates) == 1:
            member.character_name = candidates[0]

    _ORIGINAL_RESOLVE_IMPORT_CHARACTERS(plan, roster_service, build_service)

    # Make the preview explain the consolidation before anything is written.
    for member in getattr(plan, "members", ()):
        builds = list(getattr(member, "builds", ()) or ())
        if len(builds) <= 1:
            continue
        _prepared, report = consolidate_member_builds(
            builds,
            team_name=str(getattr(plan, "team_name", "") or "").strip(),
            data_root=get_data_dir(),
        )
        if report.folded_contexts:
            note = (
                f"{len(report.original_build_names)} loadouts will import as "
                f"{len(report.imported_build_names)} saved build(s) + "
                f"{len(report.folded_contexts)} context variant(s)."
            )
            if note not in member.warnings:
                member.warnings.append(note)
        for warning in report.warnings:
            if warning not in member.warnings:
                member.warnings.append(warning)


def _backup_import_state(build_service) -> None:
    """Create non-overwriting safety copies before the first destructive re-import."""
    paths = (
        (Path(build_service.builds_path), Path(build_service.builds_path).with_name("builds.before-roster-reimport.json")),
        (
            Path(build_service.canonical.catalog_path),
            Path(build_service.canonical.catalog_path).with_name("characters.before-roster-reimport.json"),
        ),
    )
    for source, backup in paths:
        if source.is_file() and not backup.exists():
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, backup)


def _build_key_from_payload(payload: dict) -> tuple[str, str, str]:
    return (
        _identity_key(payload.get("Gamertag")),
        str(payload.get("Name") or "").strip().casefold(),
        str(payload.get("BuildName") or "").strip().casefold(),
    )


def _replaceable_prior_import_keys(build_service, team_name: str, selected_players: set[str]) -> tuple[set[tuple[str, str, str]], tuple[str, ...]]:
    catalog = build_service.canonical.catalog_service.load()
    assignments = [row for row in catalog.get("team_assignments", []) if isinstance(row, dict)]
    team_key = str(team_name or "").strip().casefold()
    target_ids = {
        str(row.get("build_id") or "").strip()
        for row in assignments
        if str(row.get("team_name") or "").strip().casefold() == team_key
        and str(row.get("notes") or "").strip().casefold().startswith("imported from roster")
    }
    if not target_ids:
        return set(), ()

    protected_ids = {
        build_id
        for build_id in target_ids
        if any(
            str(row.get("build_id") or "").strip() == build_id
            and str(row.get("team_name") or "").strip().casefold() != team_key
            for row in assignments
        )
    }

    keys: set[tuple[str, str, str]] = set()
    protected_names: list[str] = []
    for build in catalog.get("builds", []):
        if not isinstance(build, dict):
            continue
        build_id = str(build.get("build_id") or "").strip()
        if build_id not in target_ids:
            continue
        legacy = build.get("legacy") if isinstance(build.get("legacy"), dict) else build.get("payload")
        legacy = legacy if isinstance(legacy, dict) else {}
        if _identity_key(legacy.get("Gamertag")) not in selected_players:
            continue
        if build_id in protected_ids:
            protected_names.append(str(build.get("name") or legacy.get("BuildName") or build_id))
            continue
        keys.add(_build_key_from_payload(legacy))
    return keys, tuple(protected_names)


def _remove_prior_imported_builds(build_service, *, team_name: str, selected_players: set[str]) -> tuple[int, tuple[str, ...]]:
    keys, protected_names = _replaceable_prior_import_keys(build_service, team_name, selected_players)
    if not keys:
        return 0, protected_names

    roster = build_service.load()
    kept = []
    removed = 0
    for build in roster.Members:
        key = (
            _identity_key(getattr(build, "Gamertag", "")),
            str(getattr(build, "Name", "") or "").strip().casefold(),
            str(getattr(build, "BuildName", "") or "").strip().casefold(),
        )
        if key in keys:
            removed += 1
            continue
        kept.append(build)

    if removed:
        _backup_import_state(build_service)
        build_service.save(BuildRoster(Members=kept))
    return removed, protected_names


def _consolidate_plan(plan) -> tuple[str, ...]:
    warnings: list[str] = []
    for member in getattr(plan, "members", ()):
        if not bool(getattr(member, "selected", True)):
            continue
        builds = list(getattr(member, "builds", ()) or ())
        if len(builds) <= 1:
            continue
        prepared, report = consolidate_member_builds(
            builds,
            team_name=str(getattr(plan, "team_name", "") or "").strip(),
            data_root=get_data_dir(),
        )
        member.builds = prepared
        warnings.extend(report.warnings)
    return tuple(warnings)


def apply_roster_import_with_context_variants(plan, roster_service, build_service, *, import_builds: bool = True):
    if not callable(_ORIGINAL_APPLY_ROSTER_IMPORT):
        raise RuntimeError("Roster context-variant import bridge is not installed.")

    team_name = str(getattr(plan, "team_name", "") or "").strip()
    selected_players = {
        _identity_key(getattr(member, "gamertag", ""))
        for member in getattr(plan, "members", ())
        if bool(getattr(member, "selected", True)) and _identity_key(getattr(member, "gamertag", ""))
    }

    replaced = 0
    protected_names: tuple[str, ...] = ()
    if import_builds and team_name and selected_players:
        replaced, protected_names = _remove_prior_imported_builds(
            build_service,
            team_name=team_name,
            selected_players=selected_players,
        )

    consolidation_warnings = _consolidate_plan(plan) if import_builds else ()
    result = _ORIGINAL_APPLY_ROSTER_IMPORT(
        plan,
        roster_service,
        build_service,
        import_builds=import_builds,
    )

    extra_warnings = list(result.warnings)
    if replaced:
        extra_warnings.append(
            f"Replaced {replaced} build(s) from the previous {team_name} roster import before saving the new import."
        )
    if protected_names:
        extra_warnings.append(
            "Kept prior imported build(s) that are also assigned to another team: "
            + ", ".join(protected_names[:6])
        )
    extra_warnings.extend(warning for warning in consolidation_warnings if warning not in extra_warnings)

    if tuple(extra_warnings) == tuple(result.warnings):
        return result
    return type(result)(
        created_roster_members=result.created_roster_members,
        updated_roster_members=result.updated_roster_members,
        imported_builds=result.imported_builds,
        skipped_builds=result.skipped_builds,
        warnings=tuple(extra_warnings),
    )


def install() -> None:
    global _INSTALLED, _ORIGINAL_APPLY_ROSTER_IMPORT, _ORIGINAL_RESOLVE_IMPORT_CHARACTERS
    if _INSTALLED:
        return

    from ui import roster_import_workflow

    _ORIGINAL_APPLY_ROSTER_IMPORT = roster_import_workflow.apply_roster_import
    _ORIGINAL_RESOLVE_IMPORT_CHARACTERS = roster_import_workflow.resolve_import_characters
    roster_import_workflow.resolve_import_characters = resolve_import_characters_with_personnel_priority
    roster_import_workflow.apply_roster_import = apply_roster_import_with_context_variants
    _INSTALLED = True


__all__ = [
    "install",
    "resolve_import_characters_with_personnel_priority",
    "apply_roster_import_with_context_variants",
]
