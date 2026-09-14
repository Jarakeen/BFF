from types import SimpleNamespace

from minmax.mundus_repository import MundusEffectRecord
from tools.audit_extreme_magicka_recovery_twice_born_star_dominance import (
    EXPECTED_SEARCH_STATE_RULE,
    LOCKED_PRIMARY_MUNDUS,
    recovery_search_state_rule,
    second_mundus_direct_recovery_ceiling,
)


class _Repo:
    def __init__(self, rows):
        self.rows = rows

    def list_names(self):
        return list(self.rows)

    def get_records(self, name):
        return list(self.rows[name])


def _record(name: str, stat_id: str, value: float, *, unit: str = "flat", supported: bool = True):
    return MundusEffectRecord(
        name=name,
        stat_id=stat_id,
        value=value,
        unit=unit,
        supported=supported,
        notes="fixture",
    )


def test_second_mundus_ceiling_excludes_locked_primary_atronach():
    repo = _Repo(
        {
            LOCKED_PRIMARY_MUNDUS: (_record(LOCKED_PRIMARY_MUNDUS, "magicka_recovery", 9999.0),),
            "The Fixture": (_record("The Fixture", "magicka_recovery", 100.0),),
        }
    )

    value, name, unresolved = second_mundus_direct_recovery_ceiling(repo)

    assert name == "The Fixture"
    assert 100.0 < value < 200.0  # seven Gold Divines amplify the base value
    assert unresolved == ()


def test_second_mundus_ceiling_reports_relevant_unsupported_record():
    repo = _Repo(
        {
            "The Fixture": (
                _record("The Fixture", "magicka_recovery", 100.0, supported=False),
            ),
        }
    )

    value, name, unresolved = second_mundus_direct_recovery_ceiling(repo)

    assert value == 0.0
    assert name is None
    assert unresolved


def test_twice_born_rule_resolves_from_shared_recovery_semantics():
    evidence = SimpleNamespace(
        set_name="Twice-Born Star",
        piece_count=5,
        candidate=SimpleNamespace(
            source_bonuses=(
                SimpleNamespace(description="You can have two Mundus Stone boons at the same time."),
            ),
            unresolved=(),
        ),
    )

    assert recovery_search_state_rule(evidence) == EXPECTED_SEARCH_STATE_RULE
