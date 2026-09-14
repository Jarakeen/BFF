from __future__ import annotations

"""Resolve roster-import identity with forgiving player and character handling.

Real raid sheets usually know a gamertag, class, and role, but not the actual toon
name. FoundryDock first reuses any character identity it can prove from saved data.
Only when no saved character exists for that player does it generate a compact,
editable character name such as ``Rik DK Tnk`` so build import can proceed without
forcing ordinary users to invent database-perfect identity by hand.

Roster personnel identity remains player-level during import: a different/new
character name for an already-known gamertag must not create a second copy of that
person in Personnel. Explicitly learned player aliases are also accepted as exact
identity evidence; aliases are never guessed from similarity.
"""

_INSTALLED = False
_ORIGINAL_NORMALIZE_ROLE = None
_ORIGINAL_NORMALIZE_CLASS = None
_ORIGINAL_APPLY_ROSTER_IMPORT = None

_CLASS_SHORT = {
    "arcanist": "Arc",
    "dragonknight": "DK",
    "necromancer": "Cro",
    "nightblade": "NB",
    "sorcerer": "Sorc",
    "templar": "Plar",
    "warden": "Den",
}

_CLASS_INPUT_ALIASES = {
    "arc": "Arcanist",
    "dk": "Dragonknight",
    "cro": "Necromancer",
    "nb": "Nightblade",
    "sorc": "Sorcerer",
    "plar": "Templar",
    "den": "Warden",
}

_ROLE_SHORT = {
    "tank": "Tnk",
    "healer": "Hlz",
    "damage dealer": "DD",
    "damage": "DD",
    "dps": "DD",
    "dd": "DD",
}

_ROLE_INPUT_ALIASES = {
    "tnk": "Tank",
    "tank": "Tank",
    "hlz": "Healer",
    "heal": "Healer",
    "heals": "Healer",
    "healer": "Healer",
    "dd": "Damage Dealer",
    "dps": "Damage Dealer",
    "damage": "Damage Dealer",
    "damage dealer": "Damage Dealer",
}


def _identity_key(value: object) -> str:
    return " ".join(str(value or "").strip().split()).lstrip("@").casefold()


def _display_gamertag(value: object) -> str:
    return " ".join(str(value or "").strip().split()).lstrip("@")


def _normalize_class_with_shorthand(value: object) -> str:
    raw = " ".join(str(value or "").strip().split())
    alias = _CLASS_INPUT_ALIASES.get(raw.casefold())
    if alias:
        return alias
    if callable(_ORIGINAL_NORMALIZE_CLASS):
        return _ORIGINAL_NORMALIZE_CLASS(value)
    return raw


def _normalize_role_with_shorthand(value: object) -> str:
    raw = " ".join(str(value or "").strip().split())
    alias = _ROLE_INPUT_ALIASES.get(raw.casefold())
    if alias:
        return alias
    if callable(_ORIGINAL_NORMALIZE_ROLE):
        return _ORIGINAL_NORMALIZE_ROLE(value)
    return raw


def _known_characters(roster_service, build_service) -> dict[str, list[tuple[str, str]]]:
    from services.roster_player_identity_service import RosterPlayerIdentityService
    from ui.roster_import_workflow import _text

    result: dict[str, list[tuple[str, str]]] = {}
    catalog = build_service.canonical.catalog_service.load()
    players = {
        _text(player.get("player_id")): _text(player.get("gamertag"))
        for player in catalog.get("players", [])
        if isinstance(player, dict)
    }

    def add(gamertag: object, name: object, eso_class: object) -> None:
        key = _identity_key(gamertag)
        character_name = _text(name)
        if not key or not character_name:
            return
        pair = (character_name, _normalize_class_with_shorthand(eso_class))
        bucket = result.setdefault(key, [])
        if pair not in bucket:
            bucket.append(pair)

    for character in catalog.get("characters", []):
        if not isinstance(character, dict):
            continue
        gamertag = players.get(
            _text(character.get("player_id")),
            _text(character.get("gamertag")),
        )
        add(gamertag, character.get("name"), character.get("eso_class"))

    identity_service = RosterPlayerIdentityService(roster_service.db)
    for member in roster_service.list_members():
        add(member.PlayerName, member.CharacterName, member.EsoClass)
        if member.Id is None:
            continue
        for alias in identity_service.aliases_for_member(int(member.Id)):
            add(alias.alias, member.CharacterName, member.EsoClass)

    return result


def _generated_character_name(member) -> str:
    player = _display_gamertag(member.gamertag)
    eso_class = _normalize_class_with_shorthand(member.eso_class)
    role = _normalize_role_with_shorthand(member.primary_role)
    class_short = _CLASS_SHORT.get(str(eso_class or "").strip().casefold(), "")
    role_short = _ROLE_SHORT.get(str(role or "").strip().casefold(), "")
    pieces = [piece for piece in (player, class_short, role_short) if piece]
    return " ".join(pieces) if len(pieces) > 1 else ""


def resolve_import_characters(plan, roster_service, build_service) -> None:
    """Reuse known toon identity first; otherwise generate a concise editable name."""
    known = _known_characters(roster_service, build_service)
    generated_names: set[str] = {
        str(member.character_name or "").strip().casefold()
        for member in plan.members
        if str(member.character_name or "").strip()
    }

    for member in plan.members:
        if str(member.character_name or "").strip():
            continue

        candidates = known.get(_identity_key(member.gamertag), [])
        wanted_class = _normalize_class_with_shorthand(member.eso_class).casefold()
        same_class = sorted(
            {
                name
                for name, eso_class in candidates
                if wanted_class and str(eso_class or "").strip().casefold() == wanted_class
            },
            key=str.casefold,
        )
        if len(same_class) == 1:
            member.character_name = same_class[0]
            continue

        unique_names = sorted({name for name, _ in candidates}, key=str.casefold)
        if len(unique_names) == 1:
            member.character_name = unique_names[0]
            continue

        # If Foundry already knows multiple possible toons for this player, do not
        # create a third synthetic identity. The preview should let the user choose.
        if candidates:
            if member.builds:
                warning = (
                    "Multiple saved characters could own this build. Choose the Character cell "
                    "in the import preview before importing builds."
                )
                if warning not in member.warnings:
                    member.warnings.append(warning)
            continue

        base_name = _generated_character_name(member)
        if base_name:
            generated = base_name
            suffix = 2
            while generated.casefold() in generated_names:
                generated = f"{base_name} {suffix}"
                suffix += 1
            member.character_name = generated
            generated_names.add(generated.casefold())
            note = f"Character name auto-filled as {generated}; edit it in the preview if you know the toon name."
            if note not in member.warnings:
                member.warnings.append(note)
            continue

        if member.builds:
            warning = (
                "Build detected, but there is not enough class/role information to create a safe "
                "character name. Choose the Character cell in the import preview first."
            )
            if warning not in member.warnings:
                member.warnings.append(warning)


def _merge_team_names(existing: object, incoming: object) -> str:
    values: list[str] = []
    seen: set[str] = set()
    for raw in f"{existing or ''},{incoming or ''}".split(","):
        name = raw.strip()
        key = name.casefold()
        if name and key not in seen:
            seen.add(key)
            values.append(name)
    return ", ".join(values)


class _PlayerUniqueRosterImportFacade:
    """Prevent a known current name or learned alias from cloning Personnel."""

    def __init__(self, roster_service):
        from services.roster_player_identity_service import RosterPlayerIdentityService

        self._service = roster_service
        self._known_members = list(roster_service.list_members())
        self._identity_service = RosterPlayerIdentityService(roster_service.db)
        self.merged_existing_count = 0

    def __getattr__(self, name):
        return getattr(self._service, name)

    def list_members(self):
        return list(self._known_members)

    def create_member(self, member):
        matches = self._identity_service.matching_members(
            getattr(member, "PlayerName", "")
        )
        if len(matches) != 1:
            created_id = self._service.create_member(member)
            member.Id = created_id
            self._known_members.append(member)
            return created_id

        # Exact current-name or explicit alias evidence means same human. Preserve
        # the existing Personnel row while canonical build import receives the
        # imported character/build through the normal path.
        target = matches[0]
        target.Team = _merge_team_names(getattr(target, "Team", ""), getattr(member, "Team", ""))
        if not str(getattr(target, "EsoClass", "") or "").strip():
            target.EsoClass = getattr(member, "EsoClass", "")
        if not str(getattr(target, "PrimaryRole", "") or "").strip():
            target.PrimaryRole = getattr(member, "PrimaryRole", "")
        if not str(getattr(target, "SecondaryRole", "") or "").strip():
            target.SecondaryRole = getattr(member, "SecondaryRole", "")
        if not str(getattr(target, "Status", "") or "").strip():
            target.Status = getattr(member, "Status", "") or "Active"
        self._service.update_member(target)
        self.merged_existing_count += 1
        return target.Id


def apply_roster_import_player_unique(plan, roster_service, build_service, *, import_builds: bool = True):
    """Run the normal importer while treating known player aliases as identity."""
    if not callable(_ORIGINAL_APPLY_ROSTER_IMPORT):
        raise RuntimeError("Roster import bridge is not installed.")

    facade = _PlayerUniqueRosterImportFacade(roster_service)
    result = _ORIGINAL_APPLY_ROSTER_IMPORT(
        plan,
        facade,
        build_service,
        import_builds=import_builds,
    )
    merged = facade.merged_existing_count
    if not merged:
        return result

    # The underlying importer counts every create_member call as "created". The
    # facade may have turned that call into a merge, so correct the user-facing
    # result without touching the importer's canonical build/team work.
    return type(result)(
        created_roster_members=max(0, result.created_roster_members - merged),
        updated_roster_members=result.updated_roster_members + merged,
        imported_builds=result.imported_builds,
        skipped_builds=result.skipped_builds,
        warnings=result.warnings,
    )


def install() -> None:
    global _INSTALLED, _ORIGINAL_NORMALIZE_ROLE, _ORIGINAL_NORMALIZE_CLASS
    global _ORIGINAL_APPLY_ROSTER_IMPORT
    if _INSTALLED:
        return

    from ui import roster_import_workflow

    _ORIGINAL_NORMALIZE_ROLE = roster_import_workflow._normalize_role
    _ORIGINAL_NORMALIZE_CLASS = roster_import_workflow._normalize_class
    _ORIGINAL_APPLY_ROSTER_IMPORT = roster_import_workflow.apply_roster_import
    roster_import_workflow._normalize_role = _normalize_role_with_shorthand
    roster_import_workflow._normalize_class = _normalize_class_with_shorthand
    roster_import_workflow.resolve_import_characters = resolve_import_characters
    roster_import_workflow.apply_roster_import = apply_roster_import_player_unique
    _INSTALLED = True


__all__ = [
    "install",
    "resolve_import_characters",
    "apply_roster_import_player_unique",
    "_normalize_class_with_shorthand",
    "_normalize_role_with_shorthand",
    "_generated_character_name",
]
