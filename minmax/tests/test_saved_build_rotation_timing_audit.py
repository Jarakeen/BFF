from models.build_model import PlayerBuild
from minmax.rotation_duration_evidence import (
    RotationDurationEvidence,
    RotationDurationResolution,
)
from minmax.rotation_plan import RotationActionKind
from minmax.saved_build_rotation_timing_audit import (
    audit_saved_build_rotation_timing,
)


def test_saved_healer_build_rotation_timing_audit_preserves_bar_and_role_context() -> None:
    build = PlayerBuild(
        Name="Magrat",
        BuildName="DF Healer",
        Role="Healer",
        FrontBarSkills=[
            "Budding Seeds",
            "Race Against Time",
            "Combat Prayer",
            "Illustrious Healing",
            "Energy Orb",
            "Eternal Guardian",
        ],
        BackBarSkills=[
            "Elemental Ring",
            "Echoing Vigor",
            "Winter's Revenge",
            "Expansive Frost Cloak",
            "Overflowing Altar",
            "Aggressive Horn",
        ],
    )

    def resolve(skill_name: str) -> RotationDurationResolution:
        if skill_name == "Combat Prayer":
            return RotationDurationResolution(
                skill_name=skill_name,
                ability_id=1,
                evidence=(
                    RotationDurationEvidence(
                        effect_name="minor_berserk",
                        duration_seconds=8.0,
                        source=skill_name,
                    ),
                    RotationDurationEvidence(
                        effect_name="minor_resolve",
                        duration_seconds=10.0,
                        source=skill_name,
                    ),
                ),
            )
        if skill_name == "Overflowing Altar":
            return RotationDurationResolution(
                skill_name=skill_name,
                ability_id=2,
                evidence=(
                    RotationDurationEvidence(
                        effect_name="altar",
                        duration_seconds=30.0,
                        source=skill_name,
                    ),
                ),
            )
        return RotationDurationResolution(
            skill_name=skill_name,
            ability_id=None,
            unresolved=("duration evidence unresolved",),
        )

    audit = audit_saved_build_rotation_timing(
        build,
        duration_resolver=resolve,
    )

    assert audit.character_name == "Magrat"
    assert audit.build_name == "DF Healer"
    assert audit.role == "Healer"
    assert len(audit.skills) == 12

    prayer = next(item for item in audit.skills if item.skill_name == "Combat Prayer")
    assert prayer.bar == "front"
    assert prayer.slot == 3
    assert prayer.kind is RotationActionKind.SKILL
    assert prayer.canonical_durations_seconds == (8.0, 10.0)

    altar = next(item for item in audit.skills if item.skill_name == "Overflowing Altar")
    assert altar.bar == "back"
    assert altar.slot == 5
    assert altar.kind is RotationActionKind.SKILL
    assert altar.canonical_durations_seconds == (30.0,)

    guardian = next(item for item in audit.skills if item.skill_name == "Eternal Guardian")
    horn = next(item for item in audit.skills if item.skill_name == "Aggressive Horn")
    assert guardian.kind is RotationActionKind.ULTIMATE
    assert horn.kind is RotationActionKind.ULTIMATE

    assert (
        "front slot 1 Budding Seeds: duration evidence unresolved"
        in audit.unresolved
    )
    assert (
        "back slot 6 Aggressive Horn: duration evidence unresolved"
        in audit.unresolved
    )


def test_saved_build_rotation_timing_audit_skips_empty_slots() -> None:
    build = PlayerBuild(
        Name="Character",
        BuildName="Build",
        Role="Damage Dealer",
        FrontBarSkills=["Skill A", "", "", "", "", "Ultimate A"],
        BackBarSkills=["", "", "", "", "", ""],
    )

    def resolve(skill_name: str) -> RotationDurationResolution:
        return RotationDurationResolution(
            skill_name=skill_name,
            ability_id=10,
            evidence=(),
        )

    audit = audit_saved_build_rotation_timing(
        build,
        duration_resolver=resolve,
    )

    assert [(item.slot, item.kind, item.skill_name) for item in audit.skills] == [
        (1, RotationActionKind.SKILL, "Skill A"),
        (6, RotationActionKind.ULTIMATE, "Ultimate A"),
    ]
    assert audit.unresolved == ()
