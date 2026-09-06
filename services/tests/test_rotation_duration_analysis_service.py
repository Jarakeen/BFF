from dataclasses import dataclass

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.skill_duration_repository import SkillDurationResolution
from services.rotation_duration_analysis_service import RotationDurationAnalysisService


@dataclass
class _FakeDurationRepository:
    values: dict[str, SkillDurationResolution]

    def resolve_name(self, name: str) -> SkillDurationResolution:
        return self.values[name]


def _plan() -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=20.0,
        actions=(
            RotationAction(0.0, 0, RotationActionKind.SKILL, "Combat Prayer", "front"),
            RotationAction(4.0, 0, RotationActionKind.SKILL, "Combat Prayer", "front"),
            RotationAction(8.0, 0, RotationActionKind.SKILL, "Instant Skill", "front"),
            RotationAction(12.0, 0, RotationActionKind.SKILL, "Combat Prayer", "front"),
        ),
    )


def test_builds_rules_only_from_positive_duration_evidence() -> None:
    service = RotationDurationAnalysisService(
        duration_repository=_FakeDurationRepository(
            {
                "Combat Prayer": SkillDurationResolution("Combat Prayer", 8.0, 101),
                "Instant Skill": SkillDurationResolution(
                    "Instant Skill",
                    None,
                    201,
                    ("Instant Skill has no positive canonical skill_rank.duration",),
                ),
            }
        )
    )

    projection = service.analyze(_plan())

    assert len(projection.rules) == 1
    assert projection.rules[0].skill_name == "Combat Prayer"
    assert projection.rules[0].duration_seconds == 8.0
    assert any("Instant Skill" in item for item in projection.unresolved)


def test_analysis_reports_premature_recast_and_uptime() -> None:
    service = RotationDurationAnalysisService(
        duration_repository=_FakeDurationRepository(
            {
                "Combat Prayer": SkillDurationResolution("Combat Prayer", 8.0, 101),
                "Instant Skill": SkillDurationResolution(
                    "Instant Skill",
                    None,
                    201,
                    ("no duration",),
                ),
            }
        )
    )

    projection = service.analyze(_plan())
    summary = projection.analysis.summaries[0]

    assert summary.cast_count == 3
    assert summary.uptime_fraction == 1.0
    assert summary.total_premature_seconds == 4.0
