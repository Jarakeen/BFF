import pytest

from models.build_model import PlayerBuild
from models.raid_plan import RaidPlan, RaidPlanMember, RaidPlanTriggeredResponsibility
from ui.raid_plan_rotation_context_bridge import RaidPlanRotationContextBridge
from ui.rotation_generate_canonical_context import RotationGenerateCanonicalContext


def _responsibility() -> RaidPlanTriggeredResponsibility:
    return RaidPlanTriggeredResponsibility(
        responsibility_id="xalvakka:pack_encounter_adds:iron_atronach",
        seat_id="off-tank",
        encounter_id="xalvakka",
        trigger_key="encounter_actor_active:iron_atronach",
        directive="acquire_and_maintain_owned_add_when_active",
        target_key="Iron Atronach",
        required_capability_type="taunt",
    )


def _plan() -> RaidPlan:
    return RaidPlan(
        plan_id="performance-mode-rg",
        trial_id="rockgrove",
        name="Performance Mode - Rockgrove",
        team_name="Performance Mode",
        members=(
            RaidPlanMember(
                seat_id="off-tank",
                gamertag="TankPlayer",
                character_name="Rylonia",
                role="Tank",
                selected_build_name="Tank Build",
            ),
        ),
        triggered_responsibilities=(_responsibility(),),
    )


def _build() -> PlayerBuild:
    return PlayerBuild(
        Name="Rylonia",
        Gamertag="TankPlayer",
        BuildName="Tank Build",
        Role="Tank",
    )


def test_bridge_freezes_exact_seat_build_and_carries_triggered_intent() -> None:
    context = RaidPlanRotationContextBridge().bind(
        base_context=RotationGenerateCanonicalContext(
            evidence_inputs=object(),  # type: ignore[arg-type]
        ),
        raid_plan=_plan(),
        seat_id="off-tank",
        saved_builds=(_build(),),
        encounter_id="xalvakka",
        provenance=("Raid Plan page handoff",),
    )

    assert context.raid_plan_id == "performance-mode-rg"
    assert context.raid_plan_seat_id == "off-tank"
    assert context.effective_build is not None
    assert context.effective_build.source_kind == "raid_plan"
    assert context.effective_build.matches(_build())
    assert len(context.raid_plan_triggered_responsibilities) == 1
    assert not hasattr(context.raid_plan_triggered_responsibilities[0], "time_seconds")


def test_bridge_rejects_unresolved_saved_build_ownership() -> None:
    with pytest.raises(ValueError, match="cannot enter Rotation Generate"):
        RaidPlanRotationContextBridge().bind(
            base_context=RotationGenerateCanonicalContext(
                evidence_inputs=object(),  # type: ignore[arg-type]
            ),
            raid_plan=_plan(),
            seat_id="off-tank",
            saved_builds=(),
            encounter_id="xalvakka",
        )
