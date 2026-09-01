from __future__ import annotations

from dataclasses import dataclass

from minmax.potion_cadence import PotionCadence
from minmax.potion_use_event import PotionUseEvent, PotionUseEventResolver
from services.build_catalog_service import BuildCatalogService


@dataclass(frozen=True)
class SavedPotionCadenceResolution:
    build_id: str
    character_id: str
    potion_name: str
    medicinal_use_rank: int | None
    event: PotionUseEvent | None = None
    cadence: PotionCadence | None = None
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return self.cadence is not None and not self.unresolved


class PotionCadenceService:
    """Bridge canonical character progression into saved-build potion cadence."""

    def __init__(
        self,
        catalog_service: BuildCatalogService,
        event_resolver: PotionUseEventResolver | None = None,
    ) -> None:
        self.catalog_service = catalog_service
        self.event_resolver = event_resolver or PotionUseEventResolver()

    def resolve_build(self, build_id: str) -> SavedPotionCadenceResolution:
        record = self.catalog_service.get_build(build_id)
        if record is None:
            return SavedPotionCadenceResolution(
                build_id=build_id,
                character_id="",
                potion_name="",
                medicinal_use_rank=None,
                unresolved=(f"Canonical build not found: {build_id}",),
            )

        character_id = str(record.get("character_id") or "").strip()
        payload = record.get("payload") if isinstance(record.get("payload"), dict) else {}
        potion_name = str(payload.get("Potion") or "").strip()
        rank = self.catalog_service.get_passive_rank(character_id, "Medicinal Use")

        if not potion_name:
            return SavedPotionCadenceResolution(
                build_id=build_id,
                character_id=character_id,
                potion_name="",
                medicinal_use_rank=rank,
                unresolved=("Saved build has no potion selection",),
            )

        if rank is None:
            return SavedPotionCadenceResolution(
                build_id=build_id,
                character_id=character_id,
                potion_name=potion_name,
                medicinal_use_rank=None,
                unresolved=(
                    f"Medicinal Use rank is not recorded for character: {character_id}",
                ),
            )

        event = self.event_resolver.resolve(potion_name)
        if not event.resolved:
            return SavedPotionCadenceResolution(
                build_id=build_id,
                character_id=character_id,
                potion_name=potion_name,
                medicinal_use_rank=rank,
                event=event,
                unresolved=event.unresolved,
            )

        cadence = PotionCadence(event, medicinal_use_rank=rank)
        return SavedPotionCadenceResolution(
            build_id=build_id,
            character_id=character_id,
            potion_name=potion_name,
            medicinal_use_rank=rank,
            event=event,
            cadence=cadence,
        )
