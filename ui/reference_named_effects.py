from __future__ import annotations

from minmax.named_combat_buffs import (
    COMPONENT_LAYER_BUFFS,
    U50_NAMED_BUFF_EFFECTS,
    U51_NAMED_BUFF_EFFECTS,
    NamedBuffEffect,
)
from ui.reference_data_model import ReferenceEntry


def _stat_name(effect: NamedBuffEffect) -> str:
    value = getattr(effect.stat, "value", str(effect.stat))
    return str(value).replace("_", " ").title()


def _effect_value(effect: NamedBuffEffect) -> str:
    value = float(effect.value)
    if effect.bucket in {"percent", "ratio_points", "resource_percent"}:
        return f"{value * 100:g}%"
    if effect.bucket == "critical_rating":
        return f"{value:g} critical rating"
    if effect.bucket == "flat":
        return f"{value:g} flat"
    return f"{value:g} {effect.bucket.replace('_', ' ')}"


def _semantics_text(effects: tuple[NamedBuffEffect, ...]) -> str:
    if not effects:
        return "Owned by a component-specific calculation layer; no standing-stat value is defined here."
    return "; ".join(f"{_stat_name(effect)}: {_effect_value(effect)}" for effect in effects)


def _paired_name(name: str) -> str | None:
    if name.startswith("Major "):
        candidate = "Minor " + name[6:]
    elif name.startswith("Minor "):
        candidate = "Major " + name[6:]
    else:
        return None
    known = set(U50_NAMED_BUFF_EFFECTS) | set(U51_NAMED_BUFF_EFFECTS) | set(COMPONENT_LAYER_BUFFS)
    return candidate if candidate in known else None


def entry_from_named_effect(name: str) -> ReferenceEntry:
    u50 = tuple(U50_NAMED_BUFF_EFFECTS.get(name, ()))
    u51 = tuple(U51_NAMED_BUFF_EFFECTS.get(name, ()))
    component_owned = name in COMPONENT_LAYER_BUFFS

    details: list[tuple[str, str]] = [
        ("Authority", "Canonical named-effect semantics"),
        ("Canonical name", name),
        ("Current modeled update", "U50"),
        ("U50 semantics", _semantics_text(u50)),
        (
            "Calculation layer",
            "Component-specific" if component_owned else "Standing / stat layer",
        ),
        (
            "Stacking rule",
            "Duplicate copies of the same named effect and objective do not stack; Major and Minor variants are distinct named effects and may stack.",
        ),
    ]

    if name not in U51_NAMED_BUFF_EFFECTS and name in U50_NAMED_BUFF_EFFECTS:
        details.append(("U51 semantics", "Name is not present in the U51 canonical table."))
    elif u51 and u51 != u50:
        details.append(("U51 semantics", _semantics_text(u51)))
    elif u51:
        details.append(("U51 semantics", "Same modeled stat semantics as U50."))
    elif component_owned:
        details.append(("U51 semantics", "Component-owned semantics; versioned magnitude is resolved by the owning calculation layer."))

    related: list[str] = []
    pair = _paired_name(name)
    if pair:
        related.append(pair)

    tags = ["NAMED EFFECT"]
    if name.startswith("Major "):
        tags.append("MAJOR")
    elif name.startswith("Minor "):
        tags.append("MINOR")
    if component_owned:
        tags.append("COMPONENT LAYER")
    else:
        tags.append("STAT LAYER")

    return ReferenceEntry(
        name=name,
        entry_type="Named Effect",
        source_scope="Global Combat",
        tags=tuple(tags),
        summary=(
            f"{name} is a canonical ESO named effect. FoundryDock keeps its named-effect identity "
            "separate from the skill, set, potion, passive, or provider that applies it."
        ),
        details=tuple(details),
        related=tuple(related),
        death_note=(
            "For death review, verify whether this named effect was active on the relevant actor or target "
            "and let the owning combat component apply its modeled contribution. Presence alone does not "
            "prove correct provider timing or raid coverage."
        ),
        field_note=(
            "Canonical named-effect semantics only. Expected uptime, preferred provider, assignment, and "
            "raid-practice ownership belong to coverage or gameplay-policy layers."
        ),
        used_by=(
            "Effects & Buff / Debuff System",
            "Rotation Builder",
            "Comp Maker",
            "Team Optimization",
            "Extreme Builder",
            "Performance / Raid Review",
        ),
        evidence=(
            "Canonical module: minmax.named_combat_buffs",
            "Stacking authority: services.named_buff_resolution_service",
        ),
    )


def build_named_effect_reference_entries() -> tuple[ReferenceEntry, ...]:
    names = set(U50_NAMED_BUFF_EFFECTS) | set(COMPONENT_LAYER_BUFFS)
    return tuple(entry_from_named_effect(name) for name in sorted(names, key=str.casefold))
