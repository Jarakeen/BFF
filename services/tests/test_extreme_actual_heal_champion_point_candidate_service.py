from __future__ import annotations

from types import SimpleNamespace

from minmax.stat_ids import StatId
from models.build_model import ChampionPointEntry, PlayerBuild
from services.extreme_actual_heal_champion_point_candidate_service import (
    ExtremeActualHealChampionPointCandidateService,
)


class _Repository:
    def __init__(self, records, effects=None, unresolved=None):
        self.records = tuple(records)
        self.by_name = {row.name.casefold(): row for row in self.records}
        self.effects = dict(effects or {})
        self.unresolved = dict(unresolved or {})

    def slottable_records(self):
        return self.records

    def resolve(self, name, max_points):
        _ = max_points
        return (
            list(self.effects.get(name, ())),
            list(self.unresolved.get(name, ())),
        )

    def get(self, name):
        return self.by_name.get(str(name or "").casefold())


def _record(name, discipline=1, description=""):
    return SimpleNamespace(
        name=name,
        discipline_index=discipline,
        max_points=50,
        description=description,
    )


def _effect(stat):
    return SimpleNamespace(stat=stat)


def test_discovers_reviewed_component_and_static_heal_relevant_cp():
    records = (
        _record("Rejuvenator"),
        _record("Soothing Tide"),
        _record("Swift Renewal"),
        _record("Arcane Supremacy"),
        _record("Fighting Finesse"),
        _record("Fortified", discipline=2),
    )
    repository = _Repository(
        records,
        effects={
            "Arcane Supremacy": (_effect(StatId.MAX_MAGICKA),),
            "Fighting Finesse": (_effect(StatId.CRITICAL_HEALING),),
            "Fortified": (_effect(StatId.PHYSICAL_RESISTANCE),),
        },
    )
    service = ExtremeActualHealChampionPointCandidateService(repository=repository)

    result = service.build_candidates(
        PlayerBuild(),
        character_id="character",
        baseline_build_id="build",
    )

    assert result.denominator_proven is True
    assert result.relevant_star_names == (
        "Arcane Supremacy",
        "Fighting Finesse",
        "Rejuvenator",
        "Soothing Tide",
        "Swift Renewal",
    )
    assert result.legal_loadout_count == 5


def test_materializes_every_legal_four_star_warfare_loadout_and_preserves_fitness():
    relevant = tuple(_record(name) for name in ("A", "B", "C", "D", "E"))
    fitness = _record("Fortified", discipline=2)
    repository = _Repository(
        (*relevant, fitness),
        effects={
            **{name: (_effect(StatId.HEALING_DONE),) for name in ("A", "B", "C", "D", "E")},
            "Fortified": (_effect(StatId.PHYSICAL_RESISTANCE),),
        },
    )
    service = ExtremeActualHealChampionPointCandidateService(repository=repository)
    baseline = PlayerBuild(
        ChampionPoints=[
            ChampionPointEntry(Name="A", Points="50"),
            ChampionPointEntry(Name="B", Points="50"),
            ChampionPointEntry(Name="C", Points="50"),
            ChampionPointEntry(Name="D", Points="50"),
            ChampionPointEntry(Name="Fortified", Points="50"),
        ]
    )

    result = service.build_candidates(
        baseline,
        character_id="character",
        baseline_build_id="build",
    )

    assert result.denominator_proven is True
    assert result.legal_loadout_count == 5
    # One of the five legal combinations is the baseline A/B/C/D bar, so only
    # the four distinct replacements need BuildCandidate objects.
    assert len(result.candidates) == 4
    observed = set()
    for candidate in result.candidates:
        entries = candidate.candidate_build.ChampionPoints
        names = {entry.Name for entry in entries}
        assert "Fortified" in names
        warfare = tuple(sorted(name for name in names if name != "Fortified"))
        assert len(warfare) == 4
        observed.add(warfare)
    assert observed == {
        ("A", "B", "C", "E"),
        ("A", "B", "D", "E"),
        ("A", "C", "D", "E"),
        ("B", "C", "D", "E"),
    }


def test_heal_relevant_unresolved_cp_blocks_denominator_instead_of_becoming_zero():
    record = _record(
        "Mysterious Mending",
        description="Increases your healing under a condition BFF has not reviewed.",
    )
    repository = _Repository(
        (record,),
        unresolved={"Mysterious Mending": ("conditional mechanic unresolved",)},
    )
    service = ExtremeActualHealChampionPointCandidateService(repository=repository)

    result = service.build_candidates(
        PlayerBuild(),
        character_id="character",
        baseline_build_id="build",
    )

    assert result.denominator_proven is False
    assert result.candidates == ()
    assert result.unresolved == (
        "Mysterious Mending: conditional mechanic unresolved",
    )


def test_unknown_saved_cp_identity_blocks_structural_replacement():
    repository = _Repository(
        (_record("Rejuvenator"),),
    )
    service = ExtremeActualHealChampionPointCandidateService(repository=repository)
    baseline = PlayerBuild(
        ChampionPoints=[ChampionPointEntry(Name="Unknown Saved Star", Points="50")]
    )

    result = service.build_candidates(
        baseline,
        character_id="character",
        baseline_build_id="build",
    )

    assert result.denominator_proven is False
    assert "not found in canonical repository" in result.unresolved[0]
