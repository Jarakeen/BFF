import sqlite3
from types import SimpleNamespace

from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from minmax.rotation_duration_evidence import resolve_rotation_duration_evidence


class _FakeSkillRepository:
    def __init__(self, database_path):
        self.database_path = database_path

    def resolve_name(self, name):
        return SimpleNamespace(
            rank=SimpleNamespace(name="Combat Prayer", ability_id=12345),
            unresolved=(),
        )


class _FakeEffectRepository:
    def __init__(self, database_path):
        self.database_path = database_path

    def resolve(self, ability_id):
        assert ability_id == 12345
        return (
            EffectVariant(
                name="minor_berserk",
                layer=EffectLayer.CAST,
                source="Combat Prayer",
                duration=8.0,
            ),
            EffectVariant(
                name="minor_resolve",
                layer=EffectLayer.CAST,
                source="Combat Prayer",
                duration=10.0,
                condition="target hit by cast",
            ),
            EffectVariant(
                name="instant_component",
                layer=EffectLayer.CAST,
                source="Combat Prayer",
                duration=None,
            ),
        )


def test_rotation_duration_evidence_preserves_multiple_effect_durations(monkeypatch) -> None:
    monkeypatch.setattr(
        "minmax.rotation_duration_evidence.SkillCoefficientRepository",
        _FakeSkillRepository,
    )
    monkeypatch.setattr(
        "minmax.rotation_duration_evidence.SkillEffectRepository",
        _FakeEffectRepository,
    )

    resolution = resolve_rotation_duration_evidence(
        " Combat Prayer ",
        database_path="ignored.db",
    )

    assert resolution.skill_name == "Combat Prayer"
    assert resolution.ability_id == 12345
    assert [
        (item.effect_name, item.duration_seconds, item.condition)
        for item in resolution.evidence
    ] == [
        ("minor_berserk", 8.0, None),
        ("minor_resolve", 10.0, "target hit by cast"),
    ]
    assert resolution.unresolved == ()


def test_rotation_duration_evidence_does_not_infer_recast_interval(monkeypatch) -> None:
    monkeypatch.setattr(
        "minmax.rotation_duration_evidence.SkillCoefficientRepository",
        _FakeSkillRepository,
    )
    monkeypatch.setattr(
        "minmax.rotation_duration_evidence.SkillEffectRepository",
        _FakeEffectRepository,
    )

    resolution = resolve_rotation_duration_evidence("Combat Prayer", database_path="ignored.db")

    assert {item.duration_seconds for item in resolution.evidence} == {8.0, 10.0}
    assert not hasattr(resolution, "recast_interval_seconds")


def test_rotation_duration_evidence_reports_missing_positive_duration(monkeypatch) -> None:
    class NoDurationEffects(_FakeEffectRepository):
        def resolve(self, ability_id):
            return (
                EffectVariant(
                    name="instant_component",
                    layer=EffectLayer.CAST,
                    source="Combat Prayer",
                    duration=None,
                ),
            )

    monkeypatch.setattr(
        "minmax.rotation_duration_evidence.SkillCoefficientRepository",
        _FakeSkillRepository,
    )
    monkeypatch.setattr(
        "minmax.rotation_duration_evidence.SkillEffectRepository",
        NoDurationEffects,
    )

    resolution = resolve_rotation_duration_evidence("Combat Prayer", database_path="ignored.db")

    assert resolution.evidence == ()
    assert resolution.unresolved == (
        "no positive canonical duration evidence found for Combat Prayer",
    )


def test_rotation_duration_evidence_preserves_skill_resolution_failure(monkeypatch) -> None:
    class MissingSkillRepository:
        def __init__(self, database_path):
            self.database_path = database_path

        def resolve_name(self, name):
            return SimpleNamespace(
                rank=None,
                unresolved=("Skill name not found: Missing Skill",),
            )

    monkeypatch.setattr(
        "minmax.rotation_duration_evidence.SkillCoefficientRepository",
        MissingSkillRepository,
    )

    resolution = resolve_rotation_duration_evidence("Missing Skill", database_path="ignored.db")

    assert resolution.skill_name == "Missing Skill"
    assert resolution.ability_id is None
    assert resolution.evidence == ()
    assert resolution.unresolved == ("Skill name not found: Missing Skill",)


def test_rotation_duration_evidence_ignores_missing_coefficients_after_identity_resolves(monkeypatch) -> None:
    class IdentityWithNoCoefficients(_FakeSkillRepository):
        def resolve_name(self, name):
            return SimpleNamespace(
                rank=SimpleNamespace(name="Combat Prayer", ability_id=12345),
                unresolved=(
                    "No coefficient rows found for combat_prayer (source ability 12345)",
                ),
            )

    monkeypatch.setattr(
        "minmax.rotation_duration_evidence.SkillCoefficientRepository",
        IdentityWithNoCoefficients,
    )
    monkeypatch.setattr(
        "minmax.rotation_duration_evidence.SkillEffectRepository",
        _FakeEffectRepository,
    )

    resolution = resolve_rotation_duration_evidence("Combat Prayer", database_path="ignored.db")

    assert resolution.ability_id == 12345
    assert resolution.evidence
    assert resolution.unresolved == ()


def test_rotation_duration_evidence_falls_back_to_imported_ability_duration(
    monkeypatch,
    tmp_path,
) -> None:
    database = tmp_path / "eso.db"
    with sqlite3.connect(database) as db:
        db.execute(
            "CREATE TABLE ability (ability_id INTEGER PRIMARY KEY, duration REAL)"
        )
        db.execute(
            "INSERT INTO ability (ability_id, duration) VALUES (?, ?)",
            (12345, 16000),
        )

    class NoLinkedDurationEffects(_FakeEffectRepository):
        def resolve(self, ability_id):
            assert ability_id == 12345
            return ()

    monkeypatch.setattr(
        "minmax.rotation_duration_evidence.SkillCoefficientRepository",
        _FakeSkillRepository,
    )
    monkeypatch.setattr(
        "minmax.rotation_duration_evidence.SkillEffectRepository",
        NoLinkedDurationEffects,
    )

    resolution = resolve_rotation_duration_evidence(
        "Combat Prayer",
        database_path=database,
    )

    assert [
        (item.effect_name, item.duration_seconds, item.source)
        for item in resolution.evidence
    ] == [
        ("ability_duration", 16.0, "Combat Prayer ability.duration"),
    ]
    assert resolution.unresolved == ()
