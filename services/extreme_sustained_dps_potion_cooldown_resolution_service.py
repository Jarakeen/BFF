from __future__ import annotations

"""Resolve canonical effective potion cooldown for one finalized Extreme build."""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from engine.config import get_data_dir
from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.passive_grant import PassiveGrant
from minmax.character_build.saved_build_adapter import SavedBuildCharacterAdapter
from minmax.jewelry_potion_cooldown_repository import JewelryPotionCooldownRepository
from minmax.jewelry_trait_repository import JewelryTraitRepository
from models.build_model import PlayerBuild


ExtremePotionPassiveGrantEvidence = ExtremeSustainedDPSPotionCooldownPassiveEvidence

ExtremePotionPassiveGrantResolver = Callable[
    [PlayerBuild, object],
    ExtremePotionPassiveGrantEvidence,
]
from services.extreme_sustained_dps_potion_cooldown_passive_grant_service import (
    ExtremeSustainedDPSPotionCooldownPassiveEvidence,
    ExtremeSustainedDPSPotionCooldownPassiveGrantService,
)
from services.extreme_skill_universe_service import ExtremeSkillUniverseService
from services.rotation_build_potion_cooldown_service import (
    RotationBuildPotionCooldownResolution,
    RotationBuildPotionCooldownService,
)
from services.rotation_saved_build_potion_cooldown_item_service import (
    RotationSavedBuildPotionCooldownItemService,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSPotionCooldownScenarioEvidence:
    effects: tuple[EffectVariant, ...] = ()
    complete: bool = False


@dataclass(frozen=True)
class ExtremeSustainedDPSPotionCooldownResolution:
    cooldown_seconds: float | None
    resolution: RotationBuildPotionCooldownResolution | None
    unresolved: tuple[str, ...] = ()

    @property
    def complete(self) -> bool:
        return self.cooldown_seconds is not None and not self.unresolved


class ExtremeSustainedDPSPotionCooldownResolutionService:
    """Bridge saved-build cooldown evidence into Objective #32 without guessing."""

    def __init__(
        self,
        *,
        database_path: str | Path | None = None,
        build_adapter: SavedBuildCharacterAdapter | None = None,
        item_service: RotationSavedBuildPotionCooldownItemService | None = None,
        cooldown_service: RotationBuildPotionCooldownService | None = None,
        passive_grant_resolver: ExtremePotionPassiveGrantResolver | None = None,
    ) -> None:
        database = Path(database_path) if database_path is not None else get_data_dir() / "eso.db"
        self.build_adapter = build_adapter or SavedBuildCharacterAdapter(database)
        self.item_service = item_service or RotationSavedBuildPotionCooldownItemService(
            JewelryPotionCooldownRepository(database),
            JewelryTraitRepository(database),
        )
        self.cooldown_service = cooldown_service or RotationBuildPotionCooldownService()
        if passive_grant_resolver is None:
            passive_service = ExtremeSustainedDPSPotionCooldownPassiveGrantService(
                ExtremeSkillUniverseService(database)
            )
            self.passive_grant_resolver = passive_service.resolve
        else:
            self.passive_grant_resolver = passive_grant_resolver

    def resolve(
        self,
        *,
        player_build: PlayerBuild,
        character_id: str | None = None,
        progression: object | None = None,
        passives: tuple[PassiveGrant, ...] = (),
        passive_inventory_complete: bool = False,
        scenario: ExtremeSustainedDPSPotionCooldownScenarioEvidence | None = None,
    ) -> ExtremeSustainedDPSPotionCooldownResolution:
        adaptation = self.build_adapter.adapt(player_build, character_id=character_id)
        unresolved = [
            str(item).strip()
            for item in tuple(adaptation.unresolved)
            if str(item).strip()
        ]
        if adaptation.build is None:
            unresolved.append("Extreme potion cooldown requires a canonical CharacterBuild")
            return ExtremeSustainedDPSPotionCooldownResolution(
                cooldown_seconds=None,
                resolution=None,
                unresolved=tuple(dict.fromkeys(unresolved)),
            )

        resolved_passives = tuple(passives)
        if passive_inventory_complete and progression is not None:
            unresolved.append(
                "Extreme potion cooldown received both explicit PassiveGrant inventory evidence and progression; choose one authority"
            )
        elif resolved_passives and progression is not None:
            unresolved.append(
                "Extreme potion cooldown received both explicit PassiveGrant evidence and progression; choose one authority"
            )
        if resolved_passives and not passive_inventory_complete:
            unresolved.append(
                "Explicit Extreme potion cooldown PassiveGrant inventory is not proven complete"
            )
        if progression is None and not resolved_passives and not passive_inventory_complete:
            unresolved.append(
                "Extreme potion cooldown requires passive progression or explicit PassiveGrant evidence"
            )
        elif progression is not None and not resolved_passives and not passive_inventory_complete:
            try:
                passive_evidence = self.passive_grant_resolver(player_build, progression)
                resolved_passives = tuple(passive_evidence.passives)
                unresolved.extend(tuple(passive_evidence.unresolved))
                if not passive_evidence.complete:
                    unresolved.append(
                        "Extreme potion cooldown passive-grant inventory is not proven complete"
                    )
            except ValueError as exc:
                unresolved.append(str(exc))

        scenario_evidence = scenario or ExtremeSustainedDPSPotionCooldownScenarioEvidence()
        if not scenario_evidence.complete:
            unresolved.append(
                "Extreme potion cooldown external scenario effect inventory is not proven complete"
            )
        if unresolved:
            return ExtremeSustainedDPSPotionCooldownResolution(
                cooldown_seconds=None,
                resolution=None,
                unresolved=tuple(dict.fromkeys(unresolved)),
            )
        item_evidence = self.item_service.resolve(player_build)
        if not hasattr(item_evidence, "unresolved"):
            return ExtremeSustainedDPSPotionCooldownResolution(
                cooldown_seconds=None,
                resolution=None,
                unresolved=(
                    "Extreme potion cooldown jewelry evidence lacks an explicit unresolved contract",
                ),
            )
        item_unresolved = tuple(getattr(item_evidence, "unresolved", ()) or ())
        if item_unresolved:
            return ExtremeSustainedDPSPotionCooldownResolution(
                cooldown_seconds=None,
                resolution=None,
                unresolved=tuple(dict.fromkeys(item_unresolved)),
            )
        resolution = self.cooldown_service.resolve(
            character_build=adaptation.build,
            item_evidence=item_evidence,
            passives=resolved_passives,
            scenario_effects=tuple(scenario_evidence.effects),
            scenario_inventory_complete=bool(scenario_evidence.complete),
        )
        unresolved.extend(tuple(resolution.effective.unresolved))
        cooldown = (
            resolution.effective.effective_cooldown_seconds
            if resolution.effective.complete and not unresolved
            else None
        )
        return ExtremeSustainedDPSPotionCooldownResolution(
            cooldown_seconds=cooldown,
            resolution=resolution,
            unresolved=tuple(dict.fromkeys(unresolved)),
        )


__all__ = [
    "ExtremePotionPassiveGrantEvidence",
    "ExtremePotionPassiveGrantResolver",    "ExtremeSustainedDPSPotionCooldownResolution",
    "ExtremeSustainedDPSPotionCooldownResolutionService",
    "ExtremeSustainedDPSPotionCooldownScenarioEvidence",
]
