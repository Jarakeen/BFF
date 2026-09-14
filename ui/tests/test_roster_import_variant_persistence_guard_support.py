from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from models.build_model import BuildRoster, PlayerBuild
from services.build_service import BuildService
from ui.roster_import_variant_persistence_guard_support import _restore_prepared_variants


def test_prepared_context_variants_are_restored_after_save_boundary(tmp_path: Path) -> None:
    service = BuildService(tmp_path / "builds.json")
    service.save(
        BuildRoster(
            Members=[
                PlayerBuild(
                    Name="Magrat",
                    Gamertag="Jarakeen",
                    BuildName="Pure Den - Trash",
                    EsoClass="Warden",
                    Role="Healer",
                )
            ]
        )
    )

    candidate = SimpleNamespace(
        build_name="Pure Den - Trash",
        eso_class="Warden",
        role="Healer",
        payload={
            "BuildName": "Pure Den - Trash",
            "EsoClass": "Warden",
            "Role": "Healer",
            "ContextVariants": [
                {
                    "ContextType": "Team + Boss",
                    "TeamName": "Swine & Punishment",
                    "BossName": "*",
                    "Armor": {"Chest": {"Set": "Pillager's Profit"}},
                    "Notes": "Imported context: Bosses",
                }
            ],
        },
    )
    member = SimpleNamespace(
        selected=True,
        gamertag="Jarakeen",
        character_name="Magrat",
        eso_class="Warden",
        primary_role="Healer",
        builds=[candidate],
    )
    plan = SimpleNamespace(members=[member])

    assert _restore_prepared_variants(plan, service) == 1
    saved = service.load().Members[0]
    assert len(saved.ContextVariants) == 1
    assert saved.ContextVariants[0].TeamName == "Swine & Punishment"
    assert saved.ContextVariants[0].BossName == "*"
    assert saved.ContextVariants[0].Armor["Chest"]["Set"] == "Pillager's Profit"


def test_build_sidebar_support_displays_build_name_and_variant_count() -> None:
    source = Path("ui/roster_import_variant_persistence_guard_support.py").read_text(encoding="utf-8")
    assert 'build_name = build.BuildName.strip() or "Default"' in source
    assert "variant_suffix" in source
    assert 'label = f"{character}  •  {build_name}{variant_suffix}"' in source
