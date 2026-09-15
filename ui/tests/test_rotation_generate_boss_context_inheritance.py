from types import SimpleNamespace

from models.build_model import BuildContextVariant, PlayerBuild
from ui.rotation_generate_application_context_provider import (
    RotationGenerateApplicationContextProvider,
)


class _BossCombo:
    def __init__(self, text: str) -> None:
        self.text = text

    def currentText(self) -> str:
        return self.text


def test_rotation_boss_context_inherits_blank_skill_slots_from_parent_build() -> None:
    base = PlayerBuild(
        Name="Magrat",
        BuildName="Regular Setup",
        Role="Healer",
        FrontBarSkills=[
            "Combat Prayer",
            "Budding Seeds",
            "Energy Orb",
            "Radiating Regeneration",
            "Echoing Vigor",
            "Reviving Barrier",
        ],
        BackBarSkills=[
            "Elemental Blockade",
            "Expansive Frost Cloak",
            "Winter's Revenge",
            "Blue Betty",
            "Overflowing Altar",
            "Aggressive Horn",
        ],
        ContextVariants=[
            BuildContextVariant(
                ContextType="Boss",
                BossName="Lylanar and Turlassil",
                FrontBarSkills=["", "", "Illustrious Healing", "", "", ""],
            )
        ],
    )
    page = SimpleNamespace(rotation_boss_combo=_BossCombo("Lylanar and Turlassil"))

    resolved = RotationGenerateApplicationContextProvider._resolved_build_for_page(
        page,
        base,
        encounter_id="lylanar_and_turlassil",
    )

    assert resolved is not base
    assert resolved.FrontBarSkills == [
        "Combat Prayer",
        "Budding Seeds",
        "Illustrious Healing",
        "Radiating Regeneration",
        "Echoing Vigor",
        "Reviving Barrier",
    ]
    assert resolved.BackBarSkills == base.BackBarSkills


def test_rotation_boss_context_with_no_skill_overrides_keeps_both_parent_bars() -> None:
    base = PlayerBuild(
        Name="Magrat",
        BuildName="Regular Setup",
        Role="Healer",
        FrontBarSkills=["A", "B", "C", "D", "E", "Front Ultimate"],
        BackBarSkills=["F", "G", "H", "I", "J", "Back Ultimate"],
        ContextVariants=[
            BuildContextVariant(
                ContextType="Boss",
                BossName="Lylanar and Turlassil",
                Food="Boss Food",
            )
        ],
    )
    page = SimpleNamespace(rotation_boss_combo=_BossCombo("Lylanar and Turlassil"))

    resolved = RotationGenerateApplicationContextProvider._resolved_build_for_page(
        page,
        base,
        encounter_id="lylanar_and_turlassil",
    )

    assert resolved.FrontBarSkills == base.FrontBarSkills
    assert resolved.BackBarSkills == base.BackBarSkills
    assert resolved.Food == "Boss Food"