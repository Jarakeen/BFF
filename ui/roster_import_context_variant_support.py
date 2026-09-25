from __future__ import annotations

"""Make roster re-imports replace prior team imports and fold loadouts into variants.

A repeated import for one team/player should replace the builds previously imported
for that same team/player, not accumulate another pile of full-build clones.  One
reviewed base loadout remains a normal saved build; boss-specific alternates become
sparse Team + Boss Context Variants when that conversion is lossless.
"""

from pathlib import Path
import shutil

from engine.config import get_data_dir
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


def _replaceable_prior_import_keys(
    build_service,
    team_name: str,
    selected_players: set[str],
) -> tuple[set[tuple[str, str, str]], tuple[str, ...], set[str]]:
    catalog = build_service.canonical.catalog_service.load_strict()
    assignments = [row for row in catalog.get("team_assignments", []) if isinstance(row, dict)]
    team_key = str(team_name or "").strip().casefold()
    target_ids = {
        str(row.get("build_id") or "").strip()
        for row in assignments
        if str(row.get("team_name") or "").strip().casefold() == team_key
        and str(row.get("notes") or "").strip().casefold().startswith("imported from roster")
    }
    if not target_ids:
        return set(), (), set()

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
    candidate_character_ids: set[str] = set()
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
        character_id = str(build.get("character_id") or "").strip()
        if character_id:
            candidate_character_ids.add(character_id)
    return keys, tuple(protected_names), candidate_character_ids


def _prune_empty_replaced_characters(
    build_service,
    *,
    candidate_character_ids: set[str],
    protected_characters: set[tuple[str, str]],
) -> int:
    if not candidate_character_ids:
        return 0

    catalog_service = build_service.canonical.catalog_service
    catalog = catalog_service.load_strict()
    remaining_character_ids = {
        str(build.get("character_id") or "").strip()
        for build in catalog.get("builds", [])
        if isinstance(build, dict)
    }
    players = {
        str(player.get("player_id") or "").strip(): _identity_key(player.get("gamertag"))
        for player in catalog.get("players", [])
        if isinstance(player, dict)
    }

    kept = []
    removed = 0
    for character in catalog.get("characters", []):
        if not isinstance(character, dict):
            kept.append(character)
            continue
        character_id = str(character.get("character_id") or "").strip()
        if character_id not in candidate_character_ids or character_id in remaining_character_ids:
            kept.append(character)
            continue
        player_key = players.get(str(character.get("player_id") or "").strip(), "")
        name_key = str(character.get("name") or "").strip().casefold()
        if (player_key, name_key) in protected_characters:
            kept.append(character)
            continue
        has_progression = bool(
            character.get("owned_skill_lines")
            or character.get("passive_ranks")
            or character.get("passive_cp_points")
        )
        if has_progression:
            kept.append(character)
            continue
        removed += 1

    if removed:
        catalog["characters"] = kept
        catalog_service.save(catalog)
    return removed


def _remove_prior_imported_builds(
    build_service,
    *,
    team_name: str,
    selected_players: set[str],
    protected_characters: set[tuple[str, str]],
) -> tuple[int, int, tuple[str, ...]]:
    keys, protected_names, candidate_character_ids = _replaceable_prior_import_keys(
        build_service, team_name, selected_players
    )
    if not keys:
        return 0, 0, protected_names

    roster = build_service.load()
    target_build_ids: list[str] = []
    for build in roster.Members:
        key = (
            _identity_key(getattr(build, "Gamertag", "")),
            str(getattr(build, "Name", "") or "").strip().casefold(),
            str(getattr(build, "BuildName", "") or "").strip().casefold(),
        )
        if key not in keys:
            continue
        build_id = str(getattr(build, "BuildId", "") or "").strip()
        if not build_id:
            raise RuntimeError(
                "Prior imported Build matched replacement criteria but has no "
                "canonical BuildId; refusing inferred deletion."
            )
        target_build_ids.append(build_id)

    removed = 0
    pruned_characters = 0
    if target_build_ids:
        _backup_import_state(build_service)
        catalog_service = build_service.canonical.catalog_service
        for build_id in target_build_ids:
            if catalog_service.delete_build(build_id):
                removed += 1
        pruned_characters = _prune_empty_replaced_characters(
            build_service,
            candidate_character_ids=candidate_character_ids,
            protected_characters=protected_characters,
        )
    return removed, pruned_characters, protected_names


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
    selected_members = [
        member
        for member in getattr(plan, "members", ())
        if bool(getattr(member, "selected", True))
    ]
    selected_players = {
        _identity_key(getattr(member, "gamertag", ""))
        for member in selected_members
        if _identity_key(getattr(member, "gamertag", ""))
    }
    protected_characters = {
        (
            _identity_key(getattr(member, "gamertag", "")),
            str(getattr(member, "character_name", "") or "").strip().casefold(),
        )
        for member in selected_members
        if _identity_key(getattr(member, "gamertag", ""))
        and str(getattr(member, "character_name", "") or "").strip()
    }

    replaced = 0
    pruned_characters = 0
    protected_names: tuple[str, ...] = ()
    if import_builds and team_name and selected_players:
        replaced, pruned_characters, protected_names = _remove_prior_imported_builds(
            build_service,
            team_name=team_name,
            selected_players=selected_players,
            protected_characters=protected_characters,
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
        message = (
            f"Replaced {replaced} build(s) from the previous {team_name} roster import before saving the new import."
        )
        if pruned_characters:
            message += f" Removed {pruned_characters} empty character record(s) created only by that prior import."
        extra_warnings.append(message)
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
