from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Iterable

from engine.config import get_data_dir
from services.ability_effect_provider_reference_service import (
    AbilityEffectProviderReference,
    AbilityEffectProviderReferenceService,
)
from services.nonability_effect_provider_reference_service import (
    NonAbilityEffectProviderReference,
    NonAbilityEffectProviderReferenceService,
    canonical_identity,
)
from ui.reference_data_model import ReferenceEntry


def _ability_provider_text(provider: AbilityEffectProviderReference) -> str:
    parts = [f"{provider.ability_name} [{provider.ability_key}]", provider.relationship]
    if provider.weapon_type:
        parts.append(f"weapon: {provider.weapon_type}")
    if provider.condition:
        parts.append(f"condition: {provider.condition}")
    if provider.confidence:
        parts.append(f"confidence: {provider.confidence}")
    return " • ".join(parts)


def _nonability_provider_text(provider: NonAbilityEffectProviderReference) -> str:
    if provider.source_kind == "gear_set":
        label = f"{provider.source_name} ({provider.piece_count}-piece)"
    elif provider.source_kind == "potion_trait":
        label = f"Potion trait: {provider.source_name}"
    else:
        label = provider.source_name

    parts = [label, provider.relationship]
    if provider.update:
        parts.append(provider.update)
    if provider.trigger:
        parts.append(f"trigger: {provider.trigger.replace('_', ' ')}")
    if provider.condition:
        parts.append(f"condition: {provider.condition.replace('_', ' ')}")
    if provider.duration is not None:
        parts.append(f"duration: {provider.duration:g}s")
    if provider.cooldown is not None:
        parts.append(f"cooldown: {provider.cooldown:g}s")
    if provider.target_count is not None:
        parts.append(f"targets: {provider.target_count}")
    if provider.range is not None:
        parts.append(f"range: {provider.range:g}m")
    if provider.scaling:
        parts.append(f"scaling: {provider.scaling}")
    return " • ".join(parts)


def enrich_reference_entries_with_ability_providers(
    entries: Iterable[ReferenceEntry],
    providers: Iterable[AbilityEffectProviderReference],
) -> tuple[ReferenceEntry, ...]:
    by_effect: dict[str, list[AbilityEffectProviderReference]] = {}
    for provider in providers:
        by_effect.setdefault(canonical_identity(provider.effect_name), []).append(provider)

    enriched: list[ReferenceEntry] = []
    for entry in entries:
        matches = tuple(by_effect.get(canonical_identity(entry.name), ()))
        if not matches:
            enriched.append(entry)
            continue

        provider_lines = tuple(_ability_provider_text(provider) for provider in matches)
        ability_names = tuple(dict.fromkeys(provider.ability_name for provider in matches))
        provenance = tuple(
            dict.fromkeys(
                f"Ability-effect provider source: {provider.source}"
                for provider in matches
                if provider.source
            )
        )
        enriched.append(
            replace(
                entry,
                details=(*entry.details, ("Reviewed ability providers", "; ".join(provider_lines))),
                related=tuple(dict.fromkeys((*entry.related, *ability_names))),
                evidence=tuple(
                    dict.fromkeys(
                        (*entry.evidence, "Canonical relationship table: ability_combat_effect", *provenance)
                    )
                ),
            )
        )

    return tuple(enriched)


def enrich_reference_entries_with_nonability_providers(
    entries: Iterable[ReferenceEntry],
    providers: Iterable[NonAbilityEffectProviderReference],
) -> tuple[ReferenceEntry, ...]:
    by_effect: dict[str, list[NonAbilityEffectProviderReference]] = {}
    for provider in providers:
        by_effect.setdefault(provider.effect_key, []).append(provider)

    enriched: list[ReferenceEntry] = []
    for entry in entries:
        matches = tuple(by_effect.get(canonical_identity(entry.name), ()))
        if not matches:
            enriched.append(entry)
            continue

        gear = tuple(provider for provider in matches if provider.source_kind == "gear_set")
        potions = tuple(provider for provider in matches if provider.source_kind == "potion_trait")
        details = list(entry.details)
        if gear:
            details.append(("Reviewed gear providers", "; ".join(_nonability_provider_text(row) for row in gear)))
        if potions:
            details.append(("Reviewed potion providers", "; ".join(_nonability_provider_text(row) for row in potions)))

        related = tuple(dict.fromkeys((*entry.related, *(row.source_name for row in matches))))
        evidence = tuple(
            dict.fromkeys((*entry.evidence, *(row.evidence for row in matches if row.evidence)))
        )
        enriched.append(replace(entry, details=tuple(details), related=related, evidence=evidence))

    return tuple(enriched)


def mark_passive_provider_gap(entries: Iterable[ReferenceEntry]) -> tuple[ReferenceEntry, ...]:
    """Keep the absence of a shared passive-provider authority explicit on named effects."""

    result: list[ReferenceEntry] = []
    for entry in entries:
        if entry.entry_type != "Named Effect":
            result.append(entry)
            continue
        result.append(
            replace(
                entry,
                details=(
                    *entry.details,
                    (
                        "Passive provider coverage",
                        "Not yet available from one shared reviewed passive-provider authority.",
                    ),
                ),
            )
        )
    return tuple(result)


def load_and_enrich_reference_entries(
    entries: Iterable[ReferenceEntry],
    database_path: Path | None = None,
) -> tuple[ReferenceEntry, ...]:
    path = database_path or (get_data_dir() / "eso.db")
    ability_service = AbilityEffectProviderReferenceService(path)
    nonability_service = NonAbilityEffectProviderReferenceService(path)

    result = enrich_reference_entries_with_ability_providers(entries, ability_service.all())
    result = enrich_reference_entries_with_nonability_providers(result, nonability_service.all())
    return mark_passive_provider_gap(result)
