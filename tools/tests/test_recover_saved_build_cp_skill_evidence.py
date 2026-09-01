from pathlib import Path

from models.build_model import PlayerBuild
import tools.recover_saved_build_cp_skill_evidence as recovery
from tools.recover_saved_build_cp_skill_evidence import (
    _output_path,
    _saved_skill_names,
)


def test_saved_skill_names_preserve_order_and_remove_duplicates():
    saved = PlayerBuild()
    saved.FrontBarSkills = ["Energy Orb", "Combat Prayer", "Energy Orb"]
    saved.BackBarSkills = ["Echoing Vigor", "Combat Prayer"]

    assert _saved_skill_names(saved) == (
        "Energy Orb",
        "Combat Prayer",
        "Echoing Vigor",
    )


def test_partial_output_path_is_build_scoped_and_not_full_harvest(tmp_path):
    path = _output_path("DF Healer", Path(tmp_path))

    assert path.name == "skill_champion_points.partial.df_healer.json"
    assert path.name != "skill_champion_points.json"


def test_verified_class_skill_url_accepts_only_matching_skill_heading(monkeypatch):
    skill = {"class_type": "Warden", "skill_line": "Green Balance"}
    monkeypatch.setattr(
        recovery,
        "fetch_html",
        lambda url: "<html><h1>Budding Seeds Skill - ESO</h1></html>",
    )

    assert recovery._verified_class_skill_url(skill, "Budding Seeds") == (
        "https://eso-hub.com/en/skills/warden/green-balance/budding-seeds"
    )

    monkeypatch.setattr(
        recovery,
        "fetch_html",
        lambda url: "<html><h1>Healing Seed Skill - ESO</h1></html>",
    )
    assert recovery._verified_class_skill_url(skill, "Budding Seeds") is None
