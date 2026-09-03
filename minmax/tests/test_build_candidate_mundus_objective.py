from types import SimpleNamespace

from minmax.build_candidate import BuildCandidate
from minmax.build_candidate_mundus_objective import healing_mundus_objective_unresolved
from minmax.stat_ids import StatId
from models.build_model import PlayerBuild


class _MundusRepository:
    def __init__(self, records):
        self.records = records

    def get_records(self, name):
        return self.records.get(name, ())


def _candidate(mundus: str) -> BuildCandidate:
    return BuildCandidate.from_build(
        character_id="magrat",
        baseline_build_id="df-healer",
        candidate_id=f"df-healer:mundus:{mundus.casefold().replace(' ', '-')}",
        candidate_build=PlayerBuild(BuildName="DF Healer", Mundus=mundus),
        changes=(),
        candidate_source="test",
    )


def test_healing_objective_blocks_critical_chance_mundus_until_expected_value_exists() -> None:
    repo = _MundusRepository(
        {
            "The Thief": (
                SimpleNamespace(stat_id=StatId.CRITICAL_CHANCE.value),
            )
        }
    )
    unresolved = healing_mundus_objective_unresolved(_candidate("The Thief"), repo)
    assert unresolved
    assert "expected critical healing is unresolved" in unresolved[0]


def test_healing_objective_blocks_critical_healing_mundus() -> None:
    repo = _MundusRepository(
        {
            "The Shadow": (
                SimpleNamespace(stat_id=StatId.CRITICAL_DAMAGE.value),
                SimpleNamespace(stat_id=StatId.CRITICAL_HEALING.value),
            )
        }
    )
    unresolved = healing_mundus_objective_unresolved(_candidate("The Shadow"), repo)
    assert len(unresolved) == 1
    assert StatId.CRITICAL_HEALING.value in unresolved[0]


def test_healing_objective_allows_noncritical_mundus_dimension() -> None:
    repo = _MundusRepository(
        {
            "The Mage": (
                SimpleNamespace(stat_id=StatId.MAX_MAGICKA.value),
            )
        }
    )
    assert healing_mundus_objective_unresolved(_candidate("The Mage"), repo) == ()
