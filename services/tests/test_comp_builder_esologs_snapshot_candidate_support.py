from pathlib import Path
from types import SimpleNamespace

from ui.comp_builder_esologs_snapshot_candidate_support import _snapshot_candidates


class _Page:
    def __init__(self, *, role: str, eso_class: str, results) -> None:
        self._role = role
        self._eso_class = eso_class
        self._esologs_top_team_results = tuple(results)

    def _cell_text(self, row: int, column: int) -> str:
        del row
        return self._role if column == 1 else ""

    def _selected_class(self, row: int) -> str:
        del row
        return self._eso_class


def _result(*players):
    return SimpleNamespace(
        TrialName="Rockgrove",
        EncounterName="Oaxiltso",
        ReportCode="ABC123",
        FightId=42,
        Players=list(players),
    )


def _player(*, role: str, eso_class: str, name: str = "Observed Tank"):
    return SimpleNamespace(
        Name=name,
        Role=role,
        ClassName=eso_class,
        GearSets=["Turning Tide", "Pearlescent Ward"],
        Abilities=["Pierce Armor", "Frost Clench"],
        Mundus="",
    )


def test_matching_esologs_tank_snapshot_becomes_selectable_candidate() -> None:
    page = _Page(
        role="Tank",
        eso_class="Dragonknight",
        results=[_result(_player(role="tank", eso_class="Dragonknight"))],
    )

    candidates = _snapshot_candidates(page, 0)

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.source_kind == "esologs_snapshot"
    assert candidate.eso_class == "Dragonknight"
    assert candidate.role == "Tank"
    assert candidate.gear_sets == ("Turning Tide", "Pearlescent Ward")
    assert candidate.skills == ("Pierce Armor", "Frost Clench")
    assert candidate.complete_build is False
    assert "Oaxiltso" in candidate.name


def test_esologs_snapshot_respects_selected_class_and_role() -> None:
    page = _Page(
        role="Tank",
        eso_class="Dragonknight",
        results=[
            _result(
                _player(role="tank", eso_class="Sorcerer", name="Wrong Class"),
                _player(role="healer", eso_class="Dragonknight", name="Wrong Role"),
            )
        ],
    )

    assert _snapshot_candidates(page, 0) == ()


def test_esologs_snapshot_support_preserves_coherent_player_rows() -> None:
    source = Path("ui/comp_builder_esologs_snapshot_candidate_support.py").read_text(
        encoding="utf-8"
    )

    assert 'getattr(page, "_esologs_top_team_results", ())' in source
    assert 'getattr(result, "Players", ())' in source
    assert 'source_kind="esologs_snapshot"' in source
    assert "Observed ESO Logs snapshot only" in source
    assert "page._esologs_top_team_results = tuple(results)" in source


def test_esologs_snapshot_candidates_install_after_trial_routing() -> None:
    installer = Path("ui/team_optimization_hybrid_anchor_support.py").read_text(
        encoding="utf-8"
    )

    trial_flow = installer.index("install_comp_builder_trial_flow()")
    snapshots = installer.index("install_comp_builder_esologs_snapshot_candidates()")
    layout = installer.index("install_comp_builder_layout()")

    assert trial_flow < snapshots < layout


def test_picker_labels_esologs_snapshot_as_esologs_not_reference() -> None:
    source = Path("ui/comp_builder_candidate_picker_support.py").read_text(
        encoding="utf-8"
    )

    assert 'if candidate.source_kind == "esologs_snapshot":' in source
    assert 'return "ESO Logs"' in source
