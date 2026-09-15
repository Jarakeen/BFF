import pytest

from models.build_model import PlayerBuild
from models.raid_plan import RaidPlan, RaidPlanMember, RaidPlanTriggeredResponsibility
from ui.rotation_generate_canonical_context import RotationGenerateCanonicalContext


def _build() -> PlayerBuild:
    return PlayerBuild(
        Name="Rylonia",
        BuildName="Tank Build",
        Role="Tank",
        EsoClass="Dragonknight",
    )


def _responsibility(
    *,
    encounter_id: str = "xalvakka",
    seat_id: str = "off-tank",
) -> RaidPlanTriggeredResponsibility:
    return RaidPlanTriggeredResponsibility(
        responsibility_id=f"{encounter_id}:pack_encounter_adds:iron_atronach",
        seat_id=seat_id,
        encounter_id=encounter_id,
        trigger_key="encounter_actor_active:iron_atronach",
        directive="acquire_and_maintain_owned_add_when_active",
        target_key="Iron Atronach",
        required_capability_type="taunt",
        source="reviewed Tank add activity",
    )


def _plan(*responsibilities: RaidPlanTriggeredResponsibility) -> RaidPlan:
    return RaidPlan(
        plan_id="performance-mode-rg",
        trial_id="rockgrove",
        name="Performance Mode - Rockgrove",
        team_name="Performance Mode",
        members=(
            RaidPlanMember(
                seat_id="off-tank",
                gamertag="TankPlayer",
                character_id="ryl-id",
                character_name="Rylonia",
                role="Tank",
                eso_class="Dragonknight",
                selected_build_name="Tank Build",
            ),
        ),
        triggered_responsibilities=tuple(responsibilities),
    )


def test_raid_plan_member_binding_freezes_exact_build_and_carries_triggered_intent() -> None:
    base = RotationGenerateCanonicalContext(
        evidence_inputs=object(),  # type: ignore[arg-type]
    )
    responsibility = _responsibility()

    context = base.with_raid_plan_member(
        raid_plan=_plan(responsibility),
        seat_id="off-tank",
        build=_build(),
        encounter_id="xalvakka",
        adjustment_labels=("off-tank encounter plan",),
        provenance=("focused Raid Plan context test",),
    )

    assert context.raid_plan_id == "performance-mode-rg"
    assert context.raid_plan_seat_id == "off-tank"
    assert context.character_id == "ryl-id"
    assert context.raid_plan_triggered_responsibilities == (responsibility,)
    assert not hasattr(context.raid_plan_triggered_responsibilities[0], "time_seconds")

    snapshot = context.effective_build
    assert snapshot is not None
    assert snapshot.source_kind == "raid_plan"
    assert snapshot.character_id == "ryl-id"
    assert snapshot.trial_id == "rockgrove"
    assert snapshot.encounter_id == "xalvakka"
    assert snapshot.team_name == "Performance Mode"
    assert snapshot.adjustment_labels == ("off-tank encounter plan",)
    assert snapshot.provenance == (
        "Raid Plan performance-mode-rg seat off-tank",
        "focused Raid Plan context test",
    )
    assert snapshot.matches(_build())


def test_raid_plan_member_binding_filters_triggered_intent_to_selected_encounter() -> None:
    xalvakka = _responsibility(encounter_id="xalvakka")
    bahsei = _responsibility(encounter_id="bahsei")
    base = RotationGenerateCanonicalContext(
        evidence_inputs=object(),  # type: ignore[arg-type]
    )

    context = base.with_raid_plan_member(
        raid_plan=_plan(xalvakka, bahsei),
        seat_id="off-tank",
        build=_build(),
        encounter_id="xalvakka",
    )

    assert context.raid_plan_triggered_responsibilities == (xalvakka,)


def test_raid_plan_member_binding_rejects_wrong_character() -> None:
    base = RotationGenerateCanonicalContext(
        evidence_inputs=object(),  # type: ignore[arg-type]
    )
    wrong = _build()
    wrong.Name = "Not Rylonia"

    with pytest.raises(ValueError, match="member character does not match"):
        base.with_raid_plan_member(
            raid_plan=_plan(),
            seat_id="off-tank",
            build=wrong,
            encounter_id="xalvakka",
        )


def test_raid_plan_member_binding_rejects_missing_canonical_character_name() -> None:
    base = RotationGenerateCanonicalContext(
        evidence_inputs=object(),  # type: ignore[arg-type]
    )
    missing = _build()
    missing.Name = ""
    missing.CharacterName = "Rylonia"  # type: ignore[attr-defined]

    with pytest.raises(ValueError, match="member character does not match"):
        base.with_raid_plan_member(
            raid_plan=_plan(),
            seat_id="off-tank",
            build=missing,
            encounter_id="xalvakka",
        )


def test_raid_plan_member_binding_rejects_wrong_selected_build() -> None:
    base = RotationGenerateCanonicalContext(
        evidence_inputs=object(),  # type: ignore[arg-type]
    )
    wrong = _build()
    wrong.BuildName = "Different Tank Build"

    with pytest.raises(ValueError, match="selected build does not match"):
        base.with_raid_plan_member(
            raid_plan=_plan(),
            seat_id="off-tank",
            build=wrong,
            encounter_id="xalvakka",
        )


def test_raid_plan_member_binding_rejects_missing_canonical_build_name() -> None:
    base = RotationGenerateCanonicalContext(
        evidence_inputs=object(),  # type: ignore[arg-type]
    )
    missing = _build()
    missing.BuildName = ""
    missing.Name = "Tank Build"

    with pytest.raises(ValueError, match="selected build does not match"):
        base.with_raid_plan_member(
            raid_plan=_plan(),
            seat_id="off-tank",
            build=missing,
            encounter_id="xalvakka",
        )


def test_raid_plan_generate_context_rejects_triggered_intent_for_another_seat() -> None:
    raid_plan_build = _build()
    bound = RotationGenerateCanonicalContext(
        evidence_inputs=object(),  # type: ignore[arg-type]
    ).with_raid_plan_member(
        raid_plan=_plan(),
        seat_id="off-tank",
        build=raid_plan_build,
        encounter_id="xalvakka",
    )

    with pytest.raises(ValueError, match="does not belong to the bound seat"):
        RotationGenerateCanonicalContext(
            evidence_inputs=object(),  # type: ignore[arg-type]
            character_id=bound.character_id,
            effective_build=bound.effective_build,
            raid_plan_id=bound.raid_plan_id,
            raid_plan_seat_id="off-tank",
            raid_plan_triggered_responsibilities=(
                _responsibility(seat_id="main-tank"),
            ),
        )
