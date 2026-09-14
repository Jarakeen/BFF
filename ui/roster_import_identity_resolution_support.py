from __future__ import annotations

"""Make roster-build import identity matching forgiving without inventing characters.

Raid spreadsheets commonly use Xbox/gamertag names while FoundryDock may store the
same player with a leading ``@``.  Character identity is still canonical and must
exist already or be chosen in the import preview; this layer only fixes equivalent
player-name matching and auto-fills a character when the match is unambiguous.
"""

_INSTALLED = False


def _identity_key(value: object) -> str:
    return " ".join(str(value or "").strip().split()).lstrip("@").casefold()


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


def resolve_import_characters(plan, roster_service, build_service) -> None:
    """Resolve only identities FoundryDock can prove from existing saved data."""
    known = _known_characters(roster_service, build_service)
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

        if member.builds:
            warning = (
                "Build detected, but FoundryDock does not know which character owns it yet. "
                "Choose the Character cell in the import preview before importing builds."
            )
            if warning not in member.warnings:
                member.warnings.append(warning)


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui import roster_import_workflow

    roster_import_workflow.resolve_import_characters = resolve_import_characters
    _INSTALLED = True


__all__ = ["install", "resolve_import_characters"]
