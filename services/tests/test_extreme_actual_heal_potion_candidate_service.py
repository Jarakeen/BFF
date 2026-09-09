from types import SimpleNamespace

from models.build_model import PlayerBuild
from services.extreme_actual_heal_potion_candidate_service import (
    ExtremeActualHealPotionCandidateService,
)


class _Choices:
    @staticmethod
    def list_choices():
        return [
            SimpleNamespace(
                label="Increase Spell Power + Restore Magicka",
                canonical_id="alchemy_family:u50:spell_power",
                traits=("Increase Spell Power", "Restore Magicka"),
            ),
            SimpleNamespace(
                label="Unstoppable",
                canonical_id="alchemy_family:u50:unstoppable",
                traits=("Unstoppable",),
            ),
        ]


def test_potion_candidate_service_emits_only_named_buff_families():
    service = ExtremeActualHealPotionCandidateService(choice_service=_Choices())
    candidates = service.build_candidates(
        PlayerBuild(BuildName="Baseline", Potion=""),
        character_id="char-1",
        baseline_build_id="build-1",
    )

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.candidate_build.Potion == "Increase Spell Power + Restore Magicka"
    assert candidate.changes[0].path == "Potion"
    assert candidate.changes[0].after["named_buffs"] == ["Major Sorcery", "Major Intellect"]


def test_potion_candidate_service_skips_current_selection():
    service = ExtremeActualHealPotionCandidateService(choice_service=_Choices())
    candidates = service.build_candidates(
        PlayerBuild(
            BuildName="Baseline",
            Potion="Increase Spell Power + Restore Magicka",
        ),
        character_id="char-1",
        baseline_build_id="build-1",
    )

    assert candidates == ()
