from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from minmax.gear_set_effect_resolver import GearSetEffectResolver
from minmax.gear_set_repository import GearSetRepository
from services.extreme_invisibility_provider_catalog_service import (
    ExtremeInvisibilityProvider,
    ExtremeInvisibilityProviderCatalog,
    ExtremeInvisibilityProviderCatalogService,
    ExtremeInvisibilityProviderStatus,
)


@dataclass(frozen=True)
class ExtremeReviewedInvisibilityGearProvider:
    name: str
    entity_id: str
    duration_seconds: float
    cooldown_seconds: float
    evidence: tuple[str, ...]


class ExtremeInvisibilityGearProviderService:
    """Discover narrowly reviewed gear-based player invisibility providers.

    The first reviewed source is Prowler's Talisman. Its canonical 1pc bonus
    explicitly states both the invisibility duration and recurrence. The parser
    accepts only that complete mechanic shape; generic tooltip keyword matching
    remains out of scope.
    """

    _PROWLERS_NAME = "Prowler's Talisman"
    _PROWLERS_PATTERN = re.compile(
        r"^While Battle Spirit is inactive, bracing while crouching turns you invisible for "
        r"(?P<duration>\d+(?:\.\d+)?) seconds?\. "
        r"This can occur once every (?P<cooldown>\d+(?:\.\d+)?) seconds?\. "
        r"Increase your chances of successfully Pickpocketing by \d+(?:\.\d+)?%\. "
        r"On dealing Critical Damage, increase your Max Magicka and Max Stamina for \d+(?:\.\d+)? seconds?, "
        r"up to \d[\d,]* at \d+ stacks\. "
        r"On dealing non-Critical Damage, increase your Health, Magicka, and Stamina Recovery for \d+(?:\.\d+)? seconds?, "
        r"up to \d[\d,]* at \d+ stacks\. "
        r"Either effect can occur up to once every \d+(?:\.\d+)? second(?:s)?\. "
        r"Talisman upgrades: \d+\.?$",
        re.IGNORECASE,
    )

    def __init__(
        self,
        database_path: str | Path,
        *,
        repository: GearSetRepository | None = None,
        description_resolver: GearSetEffectResolver | None = None,
    ) -> None:
        self.database_path = Path(database_path)
        self.repository = repository or GearSetRepository(self.database_path)
        self.description_resolver = description_resolver or GearSetEffectResolver()

    def reviewed_providers(self) -> tuple[ExtremeReviewedInvisibilityGearProvider, ...]:
        gear_set = self.repository.get_set(self._PROWLERS_NAME)
        if gear_set is None:
            return ()

        provider: ExtremeReviewedInvisibilityGearProvider | None = None
        for bonus in self.repository.get_bonuses(gear_set.id):
            if int(bonus.piece_count) != 1:
                continue
            text = self.description_resolver._clean_description(str(bonus.description or ""))
            text = " ".join(text.split())
            match = self._PROWLERS_PATTERN.fullmatch(text)
            if match is None:
                continue
            duration = float(match.group("duration"))
            cooldown = float(match.group("cooldown"))
            provider = ExtremeReviewedInvisibilityGearProvider(
                name=gear_set.name,
                entity_id="prowlers_talisman",
                duration_seconds=duration,
                cooldown_seconds=cooldown,
                evidence=(
                    f"{gear_set.name} 1pc: {duration:g}s invisibility while Battle Spirit is inactive and bracing while crouching",
                    f"{gear_set.name} 1pc: recurrence no faster than once every {cooldown:g}s",
                ),
            )
            break

        return () if provider is None else (provider,)

    def catalog(self) -> ExtremeInvisibilityProviderCatalog:
        reviewed = self.reviewed_providers()
        providers = tuple(
            ExtremeInvisibilityProvider(
                entity_id=row.entity_id,
                name=row.name,
                status=ExtremeInvisibilityProviderStatus.VERIFIED,
                duration_seconds=row.duration_seconds,
                evidence=row.evidence,
            )
            for row in reviewed
        )
        unresolved = (
            "Invisibility provider corpus is not yet exhaustive across skills, potions, and other legal sources",
        )
        return ExtremeInvisibilityProviderCatalogService.build(
            providers,
            unresolved=unresolved,
        )


__all__ = [
    "ExtremeInvisibilityGearProviderService",
    "ExtremeReviewedInvisibilityGearProvider",
]
