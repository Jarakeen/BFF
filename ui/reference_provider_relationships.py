from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Iterable

from engine.config import get_data_dir
from services.ability_effect_provider_reference_service import (
    AbilityEffectProviderReference,
    AbilityEffectProviderReferenceService,
)
from ui.reference_data_model import ReferenceEntry


def _provider_text(provider: AbilityEffectProviderReference) -> str:
    parts = [f"{provider.ability_name} [{provider.ability_key}]", provider.relationship]
    if provider.weapon_type:
        parts.append(f"weapon: {provider.weapon_type}")
    if provider.condition:
        parts.append(f"condition: {provider.condition}")
    if provider.confidence:
        parts.append(f"confidence: {provider.confidence}")
    return " • ".join(parts)


def enrich_reference_entries_with_ability_providers(
    entries: Iterable[ReferenceEntry],
    providers: Iterable[AbilityEffectProviderReference],
) -> tuple[ReferenceEntry, ...]:
    by_effect: dict[str, list[AbilityEffectProviderReference]] = {}
    for provider in providers:
        by_effect.setdefault(provider.effect_name.casefold(), []).append(provider)

    enriched: list[ReferenceEntry] = []
    for entry in entries:
        matches = tuple(by_effect.get(entry.name.casefold(), ()))
        if not matches:
            enriched.append(entry)
            continue

        provider_lines = tuple(_provider_text(provider) for provider in matches)
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


def load_and_enrich_reference_entries(
    entries: Iterable[ReferenceEntry],
    database_path: Path | None = None,
) -> tuple[ReferenceEntry, ...]:
    service = AbilityEffectProviderReferenceService(database_path or (get_data_dir() / "eso.db"))
    return enrich_reference_entries_with_ability_providers(entries, service.all())
