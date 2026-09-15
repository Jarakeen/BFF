from types import SimpleNamespace

import pytest

from models.build_model import PlayerBuild
from models.raid_plan import RaidPlan, RaidPlanMember, RaidPlanTriggeredResponsibility
from ui.raid_plan_rotation_handoff_support import RaidPlanRotationGenerateContextProvider
from ui.rotation_generate_canonical_context import RotationGenerateCanonicalContext


def _build() -> PlayerBuild:
    return PlayerBuild(
        Name="Magrat",
        Gamertag="Jarakeen",
        BuildName="DF Healer",
        Role="Healer",
    )


def _plan() -> RaidPlan:
    return RaidPlan(
        plan_id="performance-mode-rg",
        trial_id="rockgrove",
        name="Performance Mode - Rockgrove",
        team_name="Performance Mode",
        members=(
            RaidPlanMember(
                seat_id="healer-1",
                gamertag="Jarakeen",
                character_name="Magrat",
                role="Healer",
                selected_build_name="DF Healer",
                primary_assignment="Raid Healing / Support",
                secondary_assignment="Portal / Backup Control",
            ),
        ),
        triggered_responsibilities=(
            RaidPlanTriggeredResponsibility(
                responsibility_id="portal-response",
                seat_id="healer-1",
                encounter_id="xalvakka",
                trigger_key="portal_active",
                directive="Cover portal group",
            ),
        ),
    )


class _BaseProvider:
    def __init__(self) -> None:
        self.seen_build = None

    def context_for(self, page):
        self.seen_build = page._selected_build()
        return RotationGenerateCanonicalContext(evidence_inputs=object())  # type: ignore[arg-type]


class _Page:
    def __init__(self, encounter_id: str = "xalvakka") -> None:
        self.encounter_id = encounter_id

    def selected_encounter_id(self):
        return self.encounter_id


def test_provider_pins_exact_build_and_adds_raid_plan_context() -> None:
    base = _BaseProvider()
    build = _build()
    provider = RaidPlanRotationGenerateContextProvider(
        base_provider=base,
        raid_plan=_plan(),
        seat_id="healer-1",
        build=build,
    )

    context = provider.context_for(_Page())

    assert base.seen_build is not build
    assert base.seen_build.to_dict() == build.to_dict()
    assert context.raid_plan_id == "performance-mode-rg"
    assert context.raid_plan_seat_id == "healer-1"
    assert context.effective_build is not None
    assert context.effective_build.source_kind == "raid_plan"
    assert context.effective_build.matches(build)
    assert "Primary assignment: Raid Healing / Support" in context.effective_build.provenance
    assert "Secondary assignment: Portal / Backup Control" in context.effective_build.provenance
    assert len(context.raid_plan_triggered_responsibilities) == 1


def test_provider_requires_live_rotation_encounter_selection() -> None:
    provider = RaidPlanRotationGenerateContextProvider(
        base_provider=_BaseProvider(),
        raid_plan=_plan(),
        seat_id="healer-1",
        build=_build(),
    )

    with pytest.raises(ValueError, match="select an encounter"):
        provider.context_for(_Page(""))


def test_provider_does_not_turn_assignments_into_build_adjustments() -> None:
    provider = RaidPlanRotationGenerateContextProvider(
        base_provider=_BaseProvider(),
        raid_plan=_plan(),
        seat_id="healer-1",
        build=_build(),
    )

    context = provider.context_for(_Page())

    assert context.effective_build is not None
    assert context.effective_build.adjustment_labels == ()
