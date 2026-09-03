from __future__ import annotations

from models.build_model import PlayerBuild


_CP_DYNAMIC_PREFIX = "Champion Point is dynamic or not yet stat-mapped:"
_POTION_BOUNDARY_PREFIX = "Potion selected; activation/uptime is not part of static build state:"
_FROZEN_ARMOR_GAP = "Passive rank is not recorded for character: Frozen Armor"
_MOVEMENT_SPEED_MARKER = "movement_speed unresolved"

# Selected CP that are explicitly outside the current resource timeline. These
# do not change resource pools, recovery, action costs, or scheduled restoration
# in the saved-bar sustain model:
# - Breakfall: fall-damage mitigation;
# - Liquid Efficiency: item-consumption chance, while potion activations are not
#   scheduled by this runner;
# - Rationer: food/drink duration only, not the magnitude of an already-active
#   provisioning stat effect;
# - Master Gatherer: harvesting time;
# - Celerity: movement speed.
_NON_SUSTAIN_DYNAMIC_CP_KEYS = frozenset(
    {
        "breakfall",
        "liquidefficiency",
        "rationer",
        "mastergatherer",
        "celerity",
    }
)


def sustain_relevant_context_unresolved(
    build: PlayerBuild,
    messages: tuple[str, ...],
) -> tuple[str, ...]:
    """Return context diagnostics that can invalidate the modeled sustain run.

    A ``BuildCalculationContext`` is shared by many combat/stat channels, so its
    unresolved list is intentionally broader than Phase 4 sustain. This helper
    filters only boundaries whose irrelevance to the current saved-skill sustain
    model is explicit in existing architecture:

    - unmapped Champion Points not selected on the saved build are unrelated;
    - selected CP with mechanics explicitly outside this resource timeline are
      also unrelated to the current sustain result;
    - potion activation/uptime is not auto-scheduled by the sustain runner;
    - Warden Frozen Armor contributes resistance only;
    - movement speed is outside the current character-sheet resource/cost layer.

    Any other selected unmapped CP remains unresolved because it may represent a
    mechanic the player actually equipped. Every other unknown is preserved
    fail-closed.
    """

    selected_cp = {
        _key(entry.Name)
        for entry in build.ChampionPoints
        if str(entry.Name or "").strip()
    }
    relevant: list[str] = []
    seen: set[str] = set()

    for raw_message in messages:
        message = str(raw_message or "").strip()
        if not message or message in seen:
            continue
        seen.add(message)

        if message.startswith(_CP_DYNAMIC_PREFIX):
            cp_name = message[len(_CP_DYNAMIC_PREFIX):].strip()
            cp_key = _key(cp_name)
            if cp_key not in selected_cp:
                continue
            if cp_key in _NON_SUSTAIN_DYNAMIC_CP_KEYS:
                continue

        if message.startswith(_POTION_BOUNDARY_PREFIX):
            continue
        if message == _FROZEN_ARMOR_GAP:
            continue
        if _MOVEMENT_SPEED_MARKER in message:
            continue

        relevant.append(message)

    return tuple(relevant)


def _key(value: object) -> str:
    """Normalize CP identity across display names and compact canonical keys."""

    text = str(value or "").strip().casefold()
    return "".join(character for character in text if character.isalnum())
