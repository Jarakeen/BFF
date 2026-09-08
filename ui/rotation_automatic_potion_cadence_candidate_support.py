from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from engine.config import get_data_dir
from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.saved_build_adapter import SavedBuildCharacterAdapter
from minmax.jewelry_potion_cooldown_repository import JewelryPotionCooldownRepository
from minmax.jewelry_trait_repository import JewelryTraitRepository
from minmax.rotation_potion_cadence import RotationPotionCadenceRequirement
from services.rotation_build_potion_cooldown_service import (
    RotationBuildPotionCooldownResolution,
    RotationBuildPotionCooldownService,
)
from services.rotation_saved_build_potion_cooldown_item_service import (
    RotationSavedBuildPotionCooldownItemService,
)
from ui.rotation_canonical_candidate_support import (
    RotationCanonicalCandidateApplicationResult,
    RotationCanonicalCandidateSupport,
)


@dataclass(frozen=True)
class RotationPotionCooldownScenarioEvidence:
    """Explicit canonical potion-cooldown evidence for one modeled context.

    ``complete`` means the caller has inventoried the modeled scenario/context and
    these are all external potion-cooldown EffectVariants that can apply there.
    An empty-but-complete inventory is therefore meaningful evidence that the
    modeled context has no external potion-cooldown modifier.
    """

    effects: tuple[EffectVariant, ...] = ()
    complete: bool = False


class RotationAutomaticPotionCadenceCandidateSupport:
    """Derive a shared potion cadence only from complete canonical evidence.

    This adapter deliberately leaves final-plan legality, ranking, and selection to
    ``RotationCanonicalCandidateSupport``. Explicit caller-supplied cadence remains
    authoritative. Automatic cadence is only injected when item, build/passive, and
    scenario/context evidence compose to one complete effective cooldown.
    """

    def __init__(
        self,
        *,
        database_path: str | Path | None = None,
        canonical_candidates: RotationCanonicalCandidateSupport | None = None,
        build_adapter: SavedBuildCharacterAdapter | None = None,
        item_service: RotationSavedBuildPotionCooldownItemService | None = None,
        build_potion_cooldown_service: RotationBuildPotionCooldownService | None = None,
    ) -> None:
        database = Path(database_path) if database_path is not None else get_data_dir() / "eso.db"
        self.canonical_candidates = canonical_candidates or RotationCanonicalCandidateSupport(
            database_path=database,
        )
        self.build_adapter = build_adapter or SavedBuildCharacterAdapter(database)
        self.item_service = item_service or RotationSavedBuildPotionCooldownItemService(
            JewelryPotionCooldownRepository(database),
            JewelryTraitRepository(database),
        )
        self.build_potion_cooldown_service = (
            build_potion_cooldown_service or RotationBuildPotionCooldownService()
        )
        self.last_potion_cooldown_resolution: RotationBuildPotionCooldownResolution | None = None

    def run_effects(
        self,
        *,
        potion_cooldown_scenario_evidence: RotationPotionCooldownScenarioEvidence | None = None,
        **kwargs,
    ) -> RotationCanonicalCandidateApplicationResult:
        self.last_potion_cooldown_resolution = None

        # Preserve explicit already-resolved caller evidence exactly.
        if kwargs.get("potion_cadence_requirement") is not None:
            return self.canonical_candidates.run_effects(**kwargs)

        scenario = potion_cooldown_scenario_evidence
        if scenario is None:
            return self.canonical_candidates.run_effects(**kwargs)

        player_build = kwargs["player_build"]
        adaptation = self.build_adapter.adapt(
            player_build,
            character_id=kwargs.get("character_id"),
        )
        unresolved = tuple(
            str(item).strip()
            for item in adaptation.unresolved
            if str(item).strip()
        )
        character_build = adaptation.build
        if character_build is None or unresolved or not character_build.potion_id:
            # The delegate remains the single owner of adaptation failure handling.
            return self.canonical_candidates.run_effects(**kwargs)

        item_evidence = self.item_service.resolve(player_build)
        resolution = self.build_potion_cooldown_service.resolve(
            character_build=character_build,
            item_evidence=item_evidence,
            passives=tuple(kwargs.get("passives", ())),
            scenario_effects=tuple(scenario.effects),
            scenario_inventory_complete=bool(scenario.complete),
        )
        self.last_potion_cooldown_resolution = resolution

        effective = resolution.effective
        if effective.complete and effective.effective_cooldown_seconds is not None:
            kwargs["potion_cadence_requirement"] = RotationPotionCadenceRequirement(
                effective.effective_cooldown_seconds
            )

        return self.canonical_candidates.run_effects(**kwargs)


__all__ = [
    "RotationAutomaticPotionCadenceCandidateSupport",
    "RotationPotionCooldownScenarioEvidence",
]
