from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from minmax.rotation_duration_evidence import RotationDurationResolution, RotationDurationEvidence
from minmax.rotation_plan import RotationActionKind
from minmax.saved_build_maintenance_candidates import derive_saved_build_maintenance_candidates
from minmax.saved_build_rotation_timing_audit import (
    SavedBuildRotationTimingAudit,
    SavedBuildSkillTimingEvidence,
)


def _resolution(name: str, ability_id: int, *durations: float) -> RotationDurationResolution:
    evidence = tuple(
        RotationDurationEvidence(
            effect_name=f"effect_{index}",
            duration_seconds=duration,
            source=name,
        )
        for index, duration in enumerate(durations, start=1)
    )
    return RotationDurationResolution(
        skill_name=name,
        ability_id=ability_id,
        evidence=evidence,
    )


def test_saved_build_maintenance_candidates_preserve_role_neutral_timing_boundary() -> None:
    audit = SavedBuildRotationTimingAudit(
        character_name="Magrat",
        build_name="DF Healer",
        role="Healer",
        skills=(
            SavedBuildSkillTimingEvidence(
                bar="front",
                slot=1,
                kind=RotationActionKind.SKILL,
                skill_name="Budding Seeds",
                duration_resolution=_resolution("Budding Seeds", 1, 6.0),
            ),
            SavedBuildSkillTimingEvidence(
                bar="front",
                slot=3,
                kind=RotationActionKind.SKILL,
                skill_name="Combat Prayer",
                duration_resolution=_resolution("Combat Prayer", 2, 10.0, 10.0),
            ),
            SavedBuildSkillTimingEvidence(
                bar="back",
                slot=6,
                kind=RotationActionKind.ULTIMATE,
                skill_name="Aggressive Horn",
                duration_resolution=_resolution("Aggressive Horn", 3, 30.0),
            ),
        ),
    )

    result = derive_saved_build_maintenance_candidates(audit)

    assert [(item.skill_name, item.duration_seconds) for item in result.candidates] == [
        ("Budding Seeds", 6.0),
        ("Combat Prayer", 10.0),
    ]
    assert result.unresolved == ()


def test_saved_build_maintenance_candidates_leave_missing_and_ambiguous_timing_unresolved() -> None:
    audit = SavedBuildRotationTimingAudit(
        character_name="Character",
        build_name="Build",
        role="DD",
        skills=(
            SavedBuildSkillTimingEvidence(
                bar="front",
                slot=1,
                kind=RotationActionKind.SKILL,
                skill_name="Missing",
                duration_resolution=_resolution("Missing", 1),
            ),
            SavedBuildSkillTimingEvidence(
                bar="back",
                slot=2,
                kind=RotationActionKind.SKILL,
                skill_name="Ambiguous",
                duration_resolution=_resolution("Ambiguous", 2, 8.0, 12.0),
            ),
        ),
    )

    result = derive_saved_build_maintenance_candidates(audit)

    assert result.candidates == ()
    assert "no canonical duration available" in result.unresolved[0]
    assert "multiple canonical durations" in result.unresolved[1]
