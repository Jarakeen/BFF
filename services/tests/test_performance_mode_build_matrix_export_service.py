from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from models.build_model import BuildContextVariant, ChampionPointEntry, PlayerBuild
from services.performance_mode_build_matrix_export_service import (
    BuildMatrixExportRequest,
    BuildMatrixIncludeOptions,
    BuildMatrixSlotSelection,
    PerformanceModeBuildMatrixExporter,
    build_matrix_page,
    default_export_request,
)


def _build() -> PlayerBuild:
    build = PlayerBuild(
        Name="Score Pusher",
        BuildName="Primary Boss",
        EsoClass="Arcanist",
        Role="DD",
        Race="High Elf",
        Mundus="The Thief",
        AttributeMagicka=64,
        Food="Orzorga's Smoked Bear Haunch",
        Potion="Essence of Spell Power",
        FrontBarSkills=["Flail", "Fatecarver", "Trap", "Camo Hunter", "Quick Cloak", "Dawnbreaker"],
        BackBarSkills=["Scholarship", "Stampede", "Carve", "Rune", "Scalding Rune", "Languid Eye"],
        ChampionPoints=[ChampionPointEntry(Name="Deadly Aim", Points="50")],
    )
    build.Armor["Head"]["Set"] = "Slimecraw"
    build.Armor["Chest"]["Set"] = "Perfected Null Arca"
    build.ContextVariants = [
        BuildContextVariant(
            ContextType="Boss",
            BossName="Execute",
            FrontBarSkills=["", "Radiant Glory", "", "", "", ""],
            Food="Clockwork Citrus Filet",
            Notes="Execute swap at 25%.",
        ),
        BuildContextVariant(
            ContextType="Boss",
            BossName="Trash Waves",
            FrontBarSkills=["Cephaliarch's Flail", "", "", "", "", ""],
            Notes="AoE trash setup.",
        ),
        BuildContextVariant(
            ContextType="Boss",
            BossName="Portal / Solo",
            Potion="Heroism Potion",
            Notes="Portal self-sustain.",
        ),
    ]
    return build


def test_default_request_maps_named_variants_without_duplicate_assignments() -> None:
    request = default_export_request(_build())

    assert request.mode == "mapped_variants"
    mapped = {row.slot: row.variant_index for row in request.slots}
    assert mapped["boss1"] is None
    assert mapped["boss3"] == 0
    assert mapped["trash"] == 1
    assert mapped["flex"] == 2
    assigned = [value for value in mapped.values() if value is not None]
    assert len(assigned) == len(set(assigned))


def test_matrix_uses_full_baseline_and_only_variant_swaps() -> None:
    build = _build()
    request = default_export_request(build)
    page = build_matrix_page(build, request)

    boss1, _boss2, boss3, trash, flex = page.cards
    assert boss1.front_skills[0] == "Flail"
    assert boss1.sets_pieces
    assert boss3.front_skills[0] == ""
    assert boss3.front_skills[1] == "Radiant Glory"
    assert "Clockwork Citrus Filet" in boss3.food_potion
    assert trash.front_skills[0] == "Cephaliarch's Flail"
    assert "Heroism Potion" in flex.food_potion
    assert page.baseline.food == "Orzorga's Smoked Bear Haunch"
    assert "Deadly Aim" in page.baseline.cp_core


def test_export_request_is_strict_and_rejects_string_boolean() -> None:
    with pytest.raises(ValidationError):
        BuildMatrixIncludeOptions.model_validate(
            {
                "sets": "true",
                "weapons": True,
                "skills": True,
                "champion_points": True,
                "food": True,
                "potions": True,
                "class_mastery": True,
                "notes": True,
            }
        )


def test_export_request_rejects_duplicate_variant_mapping() -> None:
    with pytest.raises(ValidationError, match="cannot be mapped"):
        BuildMatrixExportRequest(
            mode="mapped_variants",
            slots=(
                BuildMatrixSlotSelection(slot="boss1", variant_index=None),
                BuildMatrixSlotSelection(slot="boss2", variant_index=0),
                BuildMatrixSlotSelection(slot="boss3", variant_index=0),
                BuildMatrixSlotSelection(slot="trash", variant_index=None),
                BuildMatrixSlotSelection(slot="flex", variant_index=None),
            ),
        )


def test_pdf_export_smoke(tmp_path: Path) -> None:
    pytest.importorskip("reportlab")
    target = tmp_path / "matrix.pdf"
    PerformanceModeBuildMatrixExporter().export_build(_build(), target)
    assert target.exists()
    assert target.stat().st_size > 1000
