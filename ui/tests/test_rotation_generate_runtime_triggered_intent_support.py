from types import SimpleNamespace

from models.build_model import PlayerBuild
from models.raid_plan import RaidPlan, RaidPlanMember, RaidPlanTriggeredResponsibility
from ui.rotation_generate_action_support import RotationGenerateActionSupport
from ui.rotation_generate_canonical_context import RotationGenerateCanonicalContext


class _Status:
    def __init__(self) -> None:
        self.infos: list[str] = []
        self.warnings: list[str] = []

    def info(self, message: str) -> None:
        self.infos.append(message)

    def warning(self, message: str) -> None:
        self.warnings.append(message)


class _Page:
    def __init__(self, context, build) -> None:
        self.rotation_generate_canonical_context = context
        self.rotation_generate_canonical_context_provider = None
        self.status = _Status()
        self.build = build
        self.bundle = SimpleNamespace(content_type="trial", ready=True)
        self.result = SimpleNamespace(
            final_plan=object(),
            cadence_evidence=None,
            canonical_result=None,
        )
        self.run_calls = []
        self.last_canonical_cadence_orchestration_result = None

    def _selected_build(self):
        return self.build

    def selected_encounter_evidence_bundle(self, _inputs):
        return self.bundle

    def run_canonical_cadence_orchestration(self, bundle, **kwargs):
        self.run_calls.append((bundle, kwargs))
        return self.result

    def selected_encounter_id(self):
        return "xalvakka"


def _bound_context():
    build = PlayerBuild(
        Name="Rylonia",
        Gamertag="TankPlayer",
        BuildName="Tank Build",
        Role="Tank",
        EsoClass="Dragonknight",
    )
    responsibility = RaidPlanTriggeredResponsibility(
        responsibility_id="xalvakka:pack_encounter_adds:iron_atronach",
        seat_id="off-tank",
        encounter_id="xalvakka",
        trigger_key="encounter_actor_active:iron_atronach",
        directive="acquire_and_maintain_owned_add_when_active",
        target_key="Iron Atronach",
        required_capability_type="taunt",
        source="reviewed Tank add activity",
    )
    plan = RaidPlan(
        plan_id="performance-mode-rg",
        trial_id="rockgrove",
        name="Performance Mode - Rockgrove",
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
        triggered_responsibilities=(responsibility,),
    )
    context = RotationGenerateCanonicalContext(
        evidence_inputs=object(),  # type: ignore[arg-type]
    ).with_raid_plan_member(
        raid_plan=plan,
        seat_id="off-tank",
        build=build,
        encounter_id="xalvakka",
    )
    return context, build


def test_generate_attaches_runtime_triggered_intent_without_changing_final_plan() -> None:
    context, build = _bound_context()
    page = _Page(context, build)
    original_plan = page.result.final_plan

    RotationGenerateActionSupport().generate(page)

    assert page.status.warnings == []
    assert len(page.run_calls) == 1
    attached = page.last_canonical_cadence_orchestration_result
    assert attached is page.result
    assert attached.final_plan is original_plan
    assert len(attached.runtime_triggered_intents) == 1
    intent = attached.runtime_triggered_intents[0]
    assert intent.source_plan_id == "performance-mode-rg"
    assert intent.source_seat_id == "off-tank"
    assert intent.trigger_key == "encounter_actor_active:iron_atronach"
    assert not hasattr(intent, "time_seconds")


def test_non_raid_plan_generate_does_not_add_runtime_triggered_intent_argument() -> None:
    build = PlayerBuild(Name="Magrat", BuildName="DF Healer", Role="Healer")
    context = RotationGenerateCanonicalContext(
        evidence_inputs=object(),  # type: ignore[arg-type]
    )
    page = _Page(context, build)

    RotationGenerateActionSupport().generate(page)

    assert len(page.run_calls) == 1
    _bundle, kwargs = page.run_calls[0]
    assert "runtime_triggered_intents" not in kwargs
    assert not hasattr(page.result, "runtime_triggered_intents")
