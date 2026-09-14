from __future__ import annotations

"""Resolve roster-import character identity with practical raid-sheet fallbacks.

Real raid sheets usually know a gamertag, class, and role, but not the actual toon
name. FoundryDock first reuses any character identity it can prove from saved data.
Only when no saved character exists for that player does it generate a compact,
editable character name such as ``Rik DK Tnk`` so build import can proceed without
forcing ordinary users to invent database-perfect identity by hand.
"""

_INSTALLED = False
_ORIGINAL_NORMALIZE_ROLE = None

_CLASS_SHORT = {
    "arcanist": "Arc",
    "dragonknight": "DK",
    "necromancer": "Cro",
    "nightblade": "NB",
    "sorcerer": "Sorc",
    "templar": "Plar",
    "warden": "Den",
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


def _normalize_role_with_shorthand(value: object) -> str:
    raw = " ".join(str(value or "").strip().split())
    alias = _ROLE_INPUT_ALIASES.get(raw.casefold())
    if alias:
        return alias
    if callable(_ORIGINAL_NORMALIZE_ROLE):
        return _ORIGINAL_NORMALIZE_ROLE(value)
    return raw


def _known_characters(roster_service, build_service) -> dict[str, list[tuple[str, str]]]:
    from ui.roster_import_workflow import _normalize_class, _text

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
        pair = (character_name, _normalize_class(eso_class))
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

    for member in roster_service.list_members():
        add(member.PlayerName, member.CharacterName, member.EsoClass)

    return result


def _generated_character_name(member) -> str:
    from ui.roster_import_workflow import _normalize_class

    player = _display_gamertag(member.gamertag)
    eso_class = _normalize_class(member.eso_class)
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
        wanted_class = str(member.eso_class or "").strip().casefold()
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


def install() -> None:
    global _INSTALLED, _ORIGINAL_NORMALIZE_ROLE
    if _INSTALLED:
        return

    from ui import roster_import_workflow

    _ORIGINAL_NORMALIZE_ROLE = roster_import_workflow._normalize_role
    roster_import_workflow._normalize_role = _normalize_role_with_shorthand
    roster_import_workflow.resolve_import_characters = resolve_import_characters
    _INSTALLED = True


__all__ = [
    "install",
    "resolve_import_characters",
    "_normalize_role_with_shorthand",
    "_generated_character_name",
]
