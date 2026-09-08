from types import SimpleNamespace

from minmax.resource_costs import ResourceType
from minmax.rotation_ability_priority import AbilityPriorityEntry
from models.build_model import PlayerBuild
from ui.rotation_dashboard_canonical_page import CanonicalRotationDashboardPage


class _Candidates:
    def __init__(self) -> None:
        self.calls = []
        self.result = SimpleNamespace(candidate_result="candidate-result")

    def run_effects(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


class _Page:
    def __init__(self) -> None:
        self.build = PlayerBuild(Name="Magrat", BuildName="DF Healer", Role="Healer")
        self.build.FrontBarSkills = ["Combat Prayer", "", "", "", "", ""]
        self.rotation_canonical_candidates = _Candidates()
        self.last_canonical_candidate_result = None
        self.last_canonical_render_evidence = None

    def _selected_build(self):
        return self.build

    def ability_priorities(self):
        return (
            AbilityPriorityEntry(
                bar="front",
                slot=1,
                skill_name="Combat Prayer",
                priority=10,
            ),
        )

    def rotation_settings(self):
        return {
            "rotation_type": "Semi-static",
            "potion": "Essence of Spell Power",
            "potion_on_cooldown": True,
            "ultimate_bar": "front",
            "starting_ultimate": 125,
            "use_scheduled_combat_attacks_for_ultimate": True,
        }

    def canonical_generation_request(self):
        return CanonicalRotationDashboardPage.canonical_generation_request(self)

    def evaluate_canonical_candidates(self, **kwargs):
        return CanonicalRotationDashboardPage.evaluate_canonical_candidates(self, **kwargs)


def test_ready_bundle_forwards_broad_coverage_for_build_scoped_candidate_discovery() -> None:
    page = _Page()
    report = object()
    bundle = SimpleNamespace(
        ready=True,
        unresolved=(),
        evaluator_resolver=object(),
        scorecard_resolver=object(),
        resource=ResourceType.MAGICKA,
        maximum_amount=32000,
        trigger_fraction=0.35,
        restoration_resolver=object(),
        demands=("encounter-demand",),
        options=(),
        wait_decision_factory=None,
        requirements=("major-brittle",),
        passives=("class-passive",),
        reserve_assessment_resolver=None,
        max_iterations=6,
        baseline_id="baseline",
        coverage_report=report,
    )

    result = CanonicalRotationDashboardPage.evaluate_canonical_evidence_bundle(
        page,
        bundle,
        character_id="magrat-id",
    )

    assert result is page.rotation_canonical_candidates.result
    assert len(page.rotation_canonical_candidates.calls) == 1
    call = page.rotation_canonical_candidates.calls[0]
    assert call["player_build"] is page.build
    assert call["coverage_report"] is report
    assert call["character_id"] == "magrat-id"
    assert call["demands"] == ("encounter-demand",)
    assert call["requirements"] == ("major-brittle",)
    assert call["passives"] == ("class-passive",)
