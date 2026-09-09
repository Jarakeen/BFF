from __future__ import annotations

from pathlib import Path

from minmax.build_candidate import BuildCandidate
from minmax.combat_effect_semantics import GameUpdate
from minmax.alchemy_potion_buff_semantics import potion_buff_for_trait
from models.build_model import PlayerBuild
from services.extreme_complete_optimization_service import ExtremeCompleteOptimizationService
from services.potion_choice_service import PotionChoiceService


class ExtremeActualHealPotionCandidateService:
    """Generate legal saved-potion family candidates for an explicit use window.

    Candidate generation proves only that a canonical potion family exists and
    carries at least one named combat buff. Whether that buff is active at the
    scored snapshot remains the responsibility of PotionUseEventResolver,
    PotionCadence, Medicinal Use progression, and the caller's elapsed time.
    """

    def __init__(
        self,
        processed_path: str | Path | None = None,
        *,
        choice_service: PotionChoiceService | None = None,
    ) -> None:
        if choice_service is None:
            path = Path(processed_path) if processed_path is not None else (
                Path(__file__).resolve().parents[1]
                / "data"
                / "processed"
                / "alchemy_effects.json"
            )
            choice_service = PotionChoiceService(path, game_update=GameUpdate.U50)
        self.choice_service = choice_service

    def build_candidates(
        self,
        baseline_build: PlayerBuild,
        *,
        character_id: str,
        baseline_build_id: str,
    ) -> tuple[BuildCandidate, ...]:
        before = " ".join(str(baseline_build.Potion or "").strip().split())
        result: list[BuildCandidate] = []
        for choice in self.choice_service.list_choices():
            label = " ".join(str(choice.label or "").strip().split())
            if not label or label.casefold() == before.casefold():
                continue
            named_buffs = tuple(
                dict.fromkeys(
                    buff
                    for trait in choice.traits
                    if (buff := potion_buff_for_trait(trait, game_update=GameUpdate.U50))
                )
            )
            if not named_buffs:
                continue

            build = PlayerBuild.from_dict(baseline_build.to_dict())
            build.Potion = label
            result.append(
                ExtremeCompleteOptimizationService._direct_candidate(
                    build,
                    character_id=character_id,
                    baseline_build_id=baseline_build_id,
                    token=f"actual-heal-potion:{choice.canonical_id}",
                    path="Potion",
                    before=before,
                    after={
                        "label": label,
                        "canonical_id": choice.canonical_id,
                        "traits": tuple(choice.traits),
                        "named_buffs": named_buffs,
                    },
                    source="extreme:actual-heal:potion-family",
                )
            )
        return tuple(result)
