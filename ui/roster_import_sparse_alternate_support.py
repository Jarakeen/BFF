from __future__ import annotations

"""Normalize human roster loadout columns before context-variant consolidation.

Raid spreadsheets commonly write the complete/default setup once and then leave
unchanged values blank in boss/portal columns. Blank alternate cells therefore mean
"inherit the base setup", not "clear this value". A player may also have multiple
class/role build families in one workbook; those families must be resolved as
separate character/build groups under the same player instead of being compared to
one another as context variants.
"""

from copy import deepcopy

_INSTALLED = False
_ORIGINAL_RESOLVE_IMPORT_CHARACTERS = None
_ORIGINAL_APPLY_ROSTER_IMPORT = None

_BASE_TOKENS = ("trash", "adds", "ads", "general", "default", "everywhere")


def _text(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _identity_key(value: object) -> str:
    return _text(value).lstrip("@").casefold()


def _family_key(candidate, member) -> tuple[str, str]:
    eso_class = _text(getattr(candidate, "eso_class", "") or getattr(member, "eso_class", "")).casefold()
    role = _text(getattr(candidate, "role", "") or getattr(member, "primary_role", "")).casefold()
    return eso_class, role


def _is_base_name(name: object) -> bool:
    folded = _text(name).casefold()
    return any(token in folded for token in _BASE_TOKENS)


def _merge_inherited(base, alternate):
    """Overlay only meaningful alternate values onto a complete base value."""
    if isinstance(base, dict) and isinstance(alternate, dict):
        result = deepcopy(base)
        for key, value in alternate.items():
            if isinstance(value, dict):
                result[key] = _merge_inherited(result.get(key, {}), value)
            elif isinstance(value, list):
                result[key] = _merge_inherited(result.get(key, []), value)
            elif isinstance(value, str):
                if value.strip():
                    result[key] = value
            elif value is not None:
                # Numeric zero is meaningful only when explicitly present in the
                # alternate payload. Parser-omitted attributes are absent entirely.
                result[key] = value
        return result

    if isinstance(base, list) and isinstance(alternate, list):
        if not alternate:
            return deepcopy(base)
        size = max(len(base), len(alternate))
        result = []
        for index in range(size):
            before = base[index] if index < len(base) else ""
            after = alternate[index] if index < len(alternate) else ""
            if isinstance(after, str) and not after.strip():
                result.append(deepcopy(before))
            elif after in (None, [], {}):
                result.append(deepcopy(before))
            else:
                result.append(deepcopy(after))
        return result

    if isinstance(alternate, str) and not alternate.strip():
        return deepcopy(base)
    if alternate in (None, [], {}):
        return deepcopy(base)
    return deepcopy(alternate)


def _inherit_family_alternates(member) -> None:
    groups: dict[tuple[str, str], list] = {}
    for candidate in list(getattr(member, "builds", ()) or ()):
        groups.setdefault(_family_key(candidate, member), []).append(candidate)

    for candidates in groups.values():
        if len(candidates) <= 1:
            continue
        base = next((candidate for candidate in candidates if _is_base_name(getattr(candidate, "build_name", ""))), candidates[0])
        base_payload = deepcopy(getattr(base, "payload", {}) or {})
        for candidate in candidates:
            if candidate is base:
                continue
            candidate.payload = _merge_inherited(base_payload, getattr(candidate, "payload", {}) or {})


def _split_multi_family_members(plan) -> None:
    expanded = []
    for member in list(getattr(plan, "members", ()) or ()):
        builds = list(getattr(member, "builds", ()) or ())
        if not builds:
            expanded.append(member)
            continue

        groups: dict[tuple[str, str], list] = {}
        for candidate in builds:
            groups.setdefault(_family_key(candidate, member), []).append(candidate)
        if len(groups) <= 1:
            expanded.append(member)
            continue

        original_class = _text(getattr(member, "eso_class", "")).casefold()
        original_character = _text(getattr(member, "character_name", ""))
        first = True
        for (eso_class_key, _role_key), family_builds in groups.items():
            clone = member if first else deepcopy(member)
            first = False
            clone.builds = family_builds
            family_class = _text(getattr(family_builds[0], "eso_class", "")) or _text(getattr(member, "eso_class", ""))
            family_role = _text(getattr(family_builds[0], "role", "")) or _text(getattr(member, "primary_role", ""))
            clone.eso_class = family_class
            clone.primary_role = family_role
            # A pre-existing character label only safely belongs to the family
            # whose class matches the original roster row. Other families should
            # resolve against canonical characters or receive an editable generated name.
            if original_character and eso_class_key != original_class:
                clone.character_name = ""
            expanded.append(clone)

    plan.members = expanded


def _prepare_plan(plan) -> None:
    _split_multi_family_members(plan)
    for member in getattr(plan, "members", ()):
        _inherit_family_alternates(member)


def _repair_team_assignments(plan, build_service) -> set[str]:
    """Attach imported builds by exact legacy identity when duplicate character rows exist."""
    team_name = _text(getattr(plan, "team_name", ""))
    if not team_name:
        return set()

    catalog_service = build_service.canonical.catalog_service
    catalog = catalog_service.load()
    repaired_build_names: set[str] = set()

    for member in getattr(plan, "members", ()):
        if not bool(getattr(member, "selected", True)):
            continue
        gamertag = _identity_key(getattr(member, "gamertag", ""))
        character_name = _text(getattr(member, "character_name", "")).casefold()
        if not gamertag or not character_name:
            continue

        for candidate in getattr(member, "builds", ()) or ():
            build_name = _text(getattr(candidate, "build_name", ""))
            if not build_name:
                continue
            matches = []
            for record in catalog.get("builds", []):
                if not isinstance(record, dict):
                    continue
                legacy = record.get("legacy") if isinstance(record.get("legacy"), dict) else record.get("payload")
                legacy = legacy if isinstance(legacy, dict) else {}
                if (
                    _identity_key(legacy.get("Gamertag")) == gamertag
                    and _text(legacy.get("Name")).casefold() == character_name
                    and _text(record.get("name") or legacy.get("BuildName")).casefold() == build_name.casefold()
                ):
                    matches.append(record)
            if len(matches) != 1:
                continue
            catalog_service.assign_build_to_team(
                build_id=_text(matches[0].get("build_id")),
                team_name=team_name,
                raid_role=_text(getattr(member, "primary_role", "") or getattr(candidate, "role", "")),
                slot_name=_text(getattr(candidate, "assignment", "") or getattr(member, "assignment", "")),
                notes="Imported from roster workbook",
            )
            repaired_build_names.add(build_name.casefold())

    return repaired_build_names


def resolve_import_characters_sparse(plan, roster_service, build_service) -> None:
    if not callable(_ORIGINAL_RESOLVE_IMPORT_CHARACTERS):
        raise RuntimeError("Sparse alternate roster import bridge is not installed.")
    _prepare_plan(plan)
    _ORIGINAL_RESOLVE_IMPORT_CHARACTERS(plan, roster_service, build_service)


def apply_roster_import_sparse(plan, roster_service, build_service, *, import_builds: bool = True):
    if not callable(_ORIGINAL_APPLY_ROSTER_IMPORT):
        raise RuntimeError("Sparse alternate roster import bridge is not installed.")
    # resolve_import_characters normally prepared the plan already. Re-running is
    # safe and makes direct/non-UI callers deterministic too.
    _prepare_plan(plan)
    result = _ORIGINAL_APPLY_ROSTER_IMPORT(
        plan,
        roster_service,
        build_service,
        import_builds=import_builds,
    )
    if not import_builds:
        return result

    repaired = _repair_team_assignments(plan, build_service)
    if not repaired:
        return result

    warnings = tuple(
        warning
        for warning in result.warnings
        if not (
            "could not uniquely attach its team assignment" in warning.casefold()
            and any(name in warning.casefold() for name in repaired)
        )
    )
    if warnings == result.warnings:
        return result
    return type(result)(
        created_roster_members=result.created_roster_members,
        updated_roster_members=result.updated_roster_members,
        imported_builds=result.imported_builds,
        skipped_builds=result.skipped_builds,
        warnings=warnings,
    )


def install() -> None:
    global _INSTALLED, _ORIGINAL_RESOLVE_IMPORT_CHARACTERS, _ORIGINAL_APPLY_ROSTER_IMPORT
    if _INSTALLED:
        return

    from ui import roster_import_workflow

    _ORIGINAL_RESOLVE_IMPORT_CHARACTERS = roster_import_workflow.resolve_import_characters
    _ORIGINAL_APPLY_ROSTER_IMPORT = roster_import_workflow.apply_roster_import
    roster_import_workflow.resolve_import_characters = resolve_import_characters_sparse
    roster_import_workflow.apply_roster_import = apply_roster_import_sparse
    _INSTALLED = True


__all__ = [
    "install",
    "resolve_import_characters_sparse",
    "apply_roster_import_sparse",
    "_merge_inherited",
    "_split_multi_family_members",
]
