import sqlite3
from types import SimpleNamespace

from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from minmax.support_effect_category import SupportEffectCategory
from minmax.support_target_type import SupportTargetType
from services.raid_planned_skill_coverage_service import (
    PlannedSkillCoverageProvider,
    RaidPlannedSkillCoverageService,
)
from services.saved_build_capability_service import RaidCoverageSnapshot


class _Repo:
    def __init__(self, effects, *, ability_id: int | None = 101):
        self.effects = effects
        self.ability_id = ability_id

    def resolve(self, ability_id):
        if self.ability_id is not None:
            assert ability_id == self.ability_id
        return tuple(self.effects)


def _database(tmp_path):
    path = tmp_path / "eso.db"
    db = sqlite3.connect(path)
    db.execute(
        "CREATE TABLE ability (ability_id INTEGER, name TEXT, class_type TEXT, "
        "skill_line TEXT, rank INTEGER, morph INTEGER)"
    )
    db.execute(
        "INSERT INTO ability VALUES "
        "(101, 'Combat Prayer', 'Templar', 'Restoring Light', 1, 1)"
    )
    db.commit()
    db.close()
    return path


def _snapshot(*names):
    return RaidCoverageSnapshot(
        {name: "unverified" for name in names},
        {name: [] for name in names},
        {name: [] for name in names},
    )


def test_planned_group_skill_counts_as_conditional_coverage(tmp_path) -> None:
    service = RaidPlannedSkillCoverageService(_database(tmp_path))
    service.skills = _Repo(
        (
            EffectVariant(
                name="minor_resolve",
                layer=EffectLayer.CAST,
                source="Combat Prayer",
                target_type=SupportTargetType.GROUP,
                category=SupportEffectCategory.BUFF,
            ),
        )
    )

    result = service.overlay(
        _snapshot("Minor Resolve"),
        (
            PlannedSkillCoverageProvider(
                seat_id="healer-1",
                provider_label="Magrat",
                eso_class="Templar",
                skills=("Combat Prayer",),
            ),
        ),
        effect_names=("Minor Resolve",),
    )

    assert result.status["Minor Resolve"] == "conditional"
    assert result.providers["Minor Resolve"] == []
    assert result.conditional_providers["Minor Resolve"] == [
        "Magrat [planned: skill: Combat Prayer]"
    ]


def test_self_only_planned_skill_does_not_count_as_group_coverage(tmp_path) -> None:
    service = RaidPlannedSkillCoverageService(_database(tmp_path))
    service.skills = _Repo(
        (
            EffectVariant(
                name="minor_resolve",
                layer=EffectLayer.CAST,
                source="Combat Prayer",
                target_type=SupportTargetType.SELF,
                category=SupportEffectCategory.BUFF,
            ),
        )
    )

    result = service.overlay(
        _snapshot("Minor Resolve"),
        (
            PlannedSkillCoverageProvider(
                seat_id="healer-1",
                provider_label="Magrat",
                eso_class="Templar",
                skills=("Combat Prayer",),
            ),
        ),
        effect_names=("Minor Resolve",),
    )

    assert result.status["Minor Resolve"] == "unverified"
    assert result.conditional_providers["Minor Resolve"] == []


def test_reviewed_group_class_passive_requires_planned_trigger_skill_line(tmp_path) -> None:
    path = _database(tmp_path)
    db = sqlite3.connect(path)
    db.execute(
        "INSERT INTO ability VALUES (?, ?, ?, ?, ?, ?)",
        (102, "Radiant Oppression", "Templar", "Dawn's Wrath", 1, 1),
    )
    db.commit()
    db.close()

    service = RaidPlannedSkillCoverageService(path)
    service.skills = _Repo((), ability_id=102)
    service.passives = SimpleNamespace(
        all=lambda: (
            SimpleNamespace(
                eso_class="Templar",
                skill_line="Dawn's Wrath",
                target="Self and group",
                effect_name="Minor Sorcery",
                passive_name="Illuminate",
            ),
        )
    )

    result = service.overlay(
        _snapshot("Minor Sorcery"),
        (
            PlannedSkillCoverageProvider(
                seat_id="healer-1",
                provider_label="Magrat",
                eso_class="Templar",
                skills=("Radiant Oppression",),
            ),
        ),
        effect_names=("Minor Sorcery",),
    )

    assert result.status["Minor Sorcery"] == "conditional"
    assert result.conditional_providers["Minor Sorcery"] == [
        "Magrat [planned: class passive: Illuminate]"
    ]


def test_class_alone_does_not_claim_passive_coverage(tmp_path) -> None:
    service = RaidPlannedSkillCoverageService(_database(tmp_path))
    service.passives = SimpleNamespace(
        all=lambda: (
            SimpleNamespace(
                eso_class="Templar",
                skill_line="Dawn's Wrath",
                target="Self and group",
                effect_name="Minor Sorcery",
                passive_name="Illuminate",
            ),
        )
    )

    result = service.overlay(
        _snapshot("Minor Sorcery"),
        (
            PlannedSkillCoverageProvider(
                seat_id="healer-1",
                provider_label="Magrat",
                eso_class="Templar",
                skills=(),
            ),
        ),
        effect_names=("Minor Sorcery",),
    )

    assert result.status["Minor Sorcery"] == "unverified"
    assert result.conditional_providers["Minor Sorcery"] == []


def test_saved_build_skill_line_can_prove_conditional_class_passive(tmp_path) -> None:
    path = _database(tmp_path)
    with sqlite3.connect(path) as db:
        db.execute(
            "INSERT INTO ability VALUES (?, ?, ?, ?, ?, ?)",
            (102, "Radiant Oppression", "Templar", "Dawn's Wrath", 1, 1),
        )
    service = RaidPlannedSkillCoverageService(path)
    service.skills = _Repo((), ability_id=102)
    service.passives = SimpleNamespace(all=lambda: (SimpleNamespace(
        eso_class="Templar", skill_line="Dawn's Wrath", target="Self and group",
        effect_name="Minor Sorcery", passive_name="Illuminate",
    ),))

    result = service.overlay(
        _snapshot("Minor Sorcery"),
        (PlannedSkillCoverageProvider(
            seat_id="dd-1", provider_label="Templar DD", eso_class="Templar",
            skills=("Radiant Oppression",), source_kind="saved build",
        ),),
        effect_names=("Minor Sorcery",),
    )

    assert result.status["Minor Sorcery"] == "conditional"
    assert result.conditional_providers["Minor Sorcery"] == [
        "Templar DD [saved build: class passive: Illuminate]"
    ]
