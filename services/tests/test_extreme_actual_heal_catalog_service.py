from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from minmax.character_progression import CharacterProgression
from models.build_model import PlayerBuild
from services import extreme_actual_heal_catalog_service as module
from services.extreme_actual_heal_catalog_service import ExtremeActualHealCatalogService
from services.extreme_heal_skill_candidate_service import ExtremeHealSkillCandidate


def _candidate(name: str, *, legal: bool = True, blockers=()):
    token = name.casefold().replace(" ", "_")
    return ExtremeHealSkillCandidate(
        entity_id=token,
        name=name,
        skill_rank_id=1,
        ability_id=1,
        rank=4,
        morph=1,
        skill_line="Green Balance",
        class_type="Warden",
        heal_component_count=1,
        can_crit=True,
        legal=legal,
        blockers=tuple(blockers),
    )


class _Candidates:
    def __init__(self, rows):
        self.rows = tuple(rows)

    def candidates_for_build(self, build, progression, *, include_blocked=False):
        _ = build, progression
        if include_blocked:
            return self.rows
        return tuple(row for row in self.rows if row.legal)


class _Optimizer:
    def __init__(self, results):
        self.results = dict(results)
        self.optimizer = SimpleNamespace(
            database_path=Path("fake.db"),
            build_service=SimpleNamespace(
                canonical=SimpleNamespace(catalog_service=object())
            ),
        )

    def optimize(self, build, entity_id, *, active_bar="front", max_passes=24):
        _ = build, active_bar, max_passes
        value = self.results[entity_id]
        if isinstance(value, Exception):
            raise value
        score, complete, unresolved = value
        return SimpleNamespace(
            optimized_event=SimpleNamespace(critical_heal=score),
            mechanic_complete=complete,
            unresolved=tuple(unresolved),
        )


def _install_progression(monkeypatch):
    resolution = SimpleNamespace(
        resolved=True,
        progression=CharacterProgression(),
        unresolved=(),
    )

    class _Adapter:
        def __init__(self, catalog):
            _ = catalog

        def resolve(self, build):
            _ = build
            return resolution

    monkeypatch.setattr(module, "MinmaxCharacterProgressionAdapter", _Adapter)


def test_catalog_tracks_highest_scored_and_highest_complete_separately(monkeypatch):
    _install_progression(monkeypatch)
    rows = (_candidate("Resolved Heal"), _candidate("Lower Bound Heal"))
    service = ExtremeActualHealCatalogService(
        optimizer=_Optimizer(
            {
                "resolved_heal": (1000.0, True, ()),
                "lower_bound_heal": (1200.0, False, ("conditional bonus unresolved",)),
            }
        ),
        candidates=_Candidates(rows),
    )

    result = service.rank(PlayerBuild(EsoClass="Warden"))

    assert result.best_scored.candidate.name == "Lower Bound Heal"
    assert result.best_scored.critical_heal == 1200.0
    assert result.best_scored.mechanic_complete is False
    assert result.best_complete.candidate.name == "Resolved Heal"
    assert result.best_complete.critical_heal == 1000.0
    assert result.global_maximum_proven is False


def test_catalog_proves_current_build_maximum_when_every_legal_candidate_is_complete(monkeypatch):
    _install_progression(monkeypatch)
    blocked = _candidate(
        "Wrong Class Heal",
        legal=False,
        blockers=("requires Templar; current build class is Warden",),
    )
    rows = (_candidate("Small Heal"), _candidate("Large Heal"), blocked)
    service = ExtremeActualHealCatalogService(
        optimizer=_Optimizer(
            {
                "small_heal": (900.0, True, ()),
                "large_heal": (1500.0, True, ()),
            }
        ),
        candidates=_Candidates(rows),
    )

    result = service.rank(PlayerBuild(EsoClass="Warden"))

    assert result.best_scored.candidate.name == "Large Heal"
    assert result.best_complete.candidate.name == "Large Heal"
    assert result.global_maximum_proven is True
    assert result.blocked_candidates == (blocked,)


def test_failed_legal_candidate_prevents_global_maximum_claim(monkeypatch):
    _install_progression(monkeypatch)
    rows = (_candidate("Known Heal"), _candidate("Broken Heal"))
    service = ExtremeActualHealCatalogService(
        optimizer=_Optimizer(
            {
                "known_heal": (1000.0, True, ()),
                "broken_heal": ValueError("critical eligibility unresolved"),
            }
        ),
        candidates=_Candidates(rows),
    )

    result = service.rank(PlayerBuild(EsoClass="Warden"))

    broken = next(entry for entry in result.entries if entry.candidate.name == "Broken Heal")
    assert broken.critical_heal is None
    assert broken.unresolved == ("critical eligibility unresolved",)
    assert result.best_scored.candidate.name == "Known Heal"
    assert result.global_maximum_proven is False


def test_equal_heals_use_stable_name_tiebreaker(monkeypatch):
    _install_progression(monkeypatch)
    rows = (_candidate("Zeta Heal"), _candidate("Alpha Heal"))
    service = ExtremeActualHealCatalogService(
        optimizer=_Optimizer(
            {
                "zeta_heal": (1000.0, True, ()),
                "alpha_heal": (1000.0, True, ()),
            }
        ),
        candidates=_Candidates(rows),
    )

    result = service.rank(PlayerBuild(EsoClass="Warden"))

    assert [entry.candidate.name for entry in result.entries] == ["Alpha Heal", "Zeta Heal"]
    assert result.best_scored.candidate.name == "Alpha Heal"
    assert result.global_maximum_proven is True
