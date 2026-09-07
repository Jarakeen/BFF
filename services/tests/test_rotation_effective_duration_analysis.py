from dataclasses import dataclass

import pytest

from minmax.rotation_effective_duration import RotationEffectiveDurationOverride
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.skill_duration_repository import SkillDurationResolution
from services.rotation_duration_analysis_service import RotationDurationAnalysisService


@dataclass
class _FakeDurationRepository:
    values: dict[str, SkillDurationResolution]

    def resolve_name(self, name: str) -> SkillDurationResolution:
        return self.values[name]


def _service() -> RotationDurationAnalysisService:
    return RotationDurationAnalysisService(
        duration_repository=_FakeDurationRepository(
            {
                "Extended Support Skill": SkillDurationResolution(
                    "Extended Support Skill",
                    8.0,
                    101,
                )
            }
        )
    )


def _plan(*, bar: str = "front") -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=40.0,
        actions=(
            RotationAction(
                0.0,
                0,
                RotationActionKind.SKILL,
                "Extended Support Skill",
                bar,
            ),
            RotationAction(
                20.0,
                0,
                RotationActionKind.SKILL,
                "Extended Support Skill",
                bar,
            ),
        ),
    )


def test_build_effective_duration_replaces_base_duration_for_recast_math() -> None:
    # Representative contract case: canonical/base duration is 8s, while the
    # selected build's already-resolved gear/passive rules extend it by 16s.
    # Rotation Maker must consume the resulting 24s duration rather than trying
    # to rediscover or hard-code why the build changed it.
    override = RotationEffectiveDurationOverride(
        skill_name="Extended Support Skill",
        duration_seconds=24.0,
        source="verified selected-build duration resolution: base 8s + 16s extension",
        bar="front",
    )

    projection = _service().analyze(
        _plan(),
        effective_duration_overrides=(override,),
    )

    assert projection.rules[0].duration_seconds == 24.0
    assert projection.effective_duration_overrides == (override,)
    summary = projection.analysis.summaries[0]
    assert summary.cast_count == 2
    assert summary.total_gap_seconds == 0.0
    assert summary.total_premature_seconds == 4.0
    assert summary.uptime_fraction == 1.0


def test_base_duration_remains_fallback_when_build_has_no_override() -> None:
    projection = _service().analyze(_plan())

    assert projection.rules[0].duration_seconds == 8.0
    assert projection.effective_duration_overrides == ()
    summary = projection.analysis.summaries[0]
    assert summary.total_gap_seconds == 24.0
    assert summary.uptime_fraction == pytest.approx(16.0 / 40.0)


def test_exact_bar_duration_evidence_wins_over_unscoped_fallback() -> None:
    generic = RotationEffectiveDurationOverride(
        skill_name="Extended Support Skill",
        duration_seconds=10.0,
        source="generic build-effective duration",
    )
    front = RotationEffectiveDurationOverride(
        skill_name="Extended Support Skill",
        duration_seconds=24.0,
        source="front-bar-specific build-effective duration",
        bar="front",
    )

    projection = _service().analyze(
        _plan(bar="front"),
        effective_duration_overrides=(generic, front),
    )

    assert projection.rules[0].duration_seconds == 24.0
    assert projection.effective_duration_overrides == (front,)


def test_duplicate_effective_duration_evidence_fails_closed() -> None:
    first = RotationEffectiveDurationOverride(
        skill_name="Extended Support Skill",
        duration_seconds=20.0,
        source="source one",
        bar="front",
    )
    second = RotationEffectiveDurationOverride(
        skill_name="extended support skill",
        duration_seconds=24.0,
        source="source two",
        bar="front",
    )

    with pytest.raises(ValueError, match="duplicate effective rotation duration"):
        _service().analyze(
            _plan(),
            effective_duration_overrides=(first, second),
        )


def test_effective_duration_requires_provenance() -> None:
    with pytest.raises(ValueError, match="needs provenance source"):
        RotationEffectiveDurationOverride(
            skill_name="Extended Support Skill",
            duration_seconds=24.0,
            source="",
        )
