import sqlite3
from types import SimpleNamespace

from minmax.skill_component_classification import (
    HealTemporalScope,
    SkillComponentClassification,
    SkillEffectKind,
)
from services.rotation_healer_canonical_delayed_timing_service import (
    RotationHealerCanonicalDelayedTimingService,
)


class _FakeCoefficients:
    def __init__(self, *, rank=True):
        self.rank_enabled = rank

    def resolve_name(self, name):
        if not self.rank_enabled:
            return SimpleNamespace(rank=None, unresolved=(f"skill not found: {name}",))
        return SimpleNamespace(
            rank=SimpleNamespace(
                name="Budding Seeds",
                skill_rank_id=6910,
                ability_id=93807,
            ),
            unresolved=(),
        )


class _FakeComponents:
    def __init__(self, classification):
        self.classification = classification

    def get_component(self, skill_rank_id, coefficient_number):
        return self.classification


def _classification(*, temporal=HealTemporalScope.DELAYED, kind=SkillEffectKind.HEAL):
    return SkillComponentClassification(
        skill_rank_id=6910,
        coefficient_number=1,
        effect_kind=kind,
        is_dot=False,
        source="test",
        confidence=1.0,
        heal_temporal_scope=temporal,
    )


def _database(tmp_path, description):
    path = tmp_path / "eso.db"
    with sqlite3.connect(path) as db:
        db.execute(
            "CREATE TABLE ability (ability_id INTEGER PRIMARY KEY, coef_description TEXT)"
        )
        db.execute(
            "INSERT INTO ability(ability_id, coef_description) VALUES (?, ?)",
            (93807, description),
        )
    return path


def test_resolves_budding_seeds_bloom_after_six_seconds(tmp_path):
    path = _database(
        tmp_path,
        "Summon a field of flowers which blooms after 6 seconds, healing you and allies in the area for $1 Health.",
    )
    result = RotationHealerCanonicalDelayedTimingService(
        path,
        coefficient_repository=_FakeCoefficients(),
        component_repository=_FakeComponents(_classification()),
    ).resolve(source_name="Budding Seeds", coefficient_number=1)

    assert result.ready
    assert result.runtime_evidence is not None
    assert result.runtime_evidence.delay_seconds == 6.0
    assert result.skill_rank_id == 6910
    assert result.ability_id == 93807
    assert "after 6 seconds" in result.component_fragment
    assert any("after 6 seconds" in item for item in result.evidence)


def test_over_duration_does_not_become_delayed_offset(tmp_path):
    path = _database(
        tmp_path,
        "Heal you and allies for $1 Health over 6 seconds.",
    )
    result = RotationHealerCanonicalDelayedTimingService(
        path,
        coefficient_repository=_FakeCoefficients(),
        component_repository=_FakeComponents(_classification()),
    ).resolve(source_name="Budding Seeds", coefficient_number=1)

    assert not result.ready
    assert result.runtime_evidence is None
    assert result.unresolved == (
        "Budding Seeds coefficient 1: explicit delayed-heal offset is unresolved",
    )


def test_non_delayed_heal_identity_fails_closed_even_if_text_mentions_after_seconds(tmp_path):
    path = _database(
        tmp_path,
        "After 6 seconds, healing you and allies in the area for $1 Health.",
    )
    result = RotationHealerCanonicalDelayedTimingService(
        path,
        coefficient_repository=_FakeCoefficients(),
        component_repository=_FakeComponents(
            _classification(temporal=HealTemporalScope.DIRECT)
        ),
    ).resolve(source_name="Budding Seeds", coefficient_number=1)

    assert not result.ready
    assert result.runtime_evidence is None
    assert result.unresolved == (
        "Budding Seeds coefficient 1: component is not canonically classified as delayed healing",
    )


def test_non_heal_identity_fails_closed(tmp_path):
    path = _database(
        tmp_path,
        "After 6 seconds, dealing $1 Magic Damage.",
    )
    result = RotationHealerCanonicalDelayedTimingService(
        path,
        coefficient_repository=_FakeCoefficients(),
        component_repository=_FakeComponents(
            _classification(kind=SkillEffectKind.DAMAGE)
        ),
    ).resolve(source_name="Budding Seeds", coefficient_number=1)

    assert not result.ready
    assert result.runtime_evidence is None
    assert result.unresolved[0] == (
        "Budding Seeds coefficient 1: component is not canonically classified as healing"
    )


def test_unknown_skill_preserves_identity_gap(tmp_path):
    path = _database(
        tmp_path,
        "Summon a field which blooms after 6 seconds, healing for $1 Health.",
    )
    result = RotationHealerCanonicalDelayedTimingService(
        path,
        coefficient_repository=_FakeCoefficients(rank=False),
        component_repository=_FakeComponents(_classification()),
    ).resolve(source_name="Imaginary Bloom", coefficient_number=1)

    assert not result.ready
    assert result.skill_rank_id is None
    assert result.runtime_evidence is None
    assert result.unresolved == ("skill not found: Imaginary Bloom",)
