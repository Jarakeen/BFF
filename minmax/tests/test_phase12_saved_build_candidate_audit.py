from types import SimpleNamespace

from minmax.build_candidate import BuildCandidate, BuildChange
from minmax.build_candidate_comparison import BuildCandidateComparison
from minmax.build_candidate_healing import ModeledHealingPotency
from minmax.evaluation_objective import EvaluationObjective
from minmax.skill_component_classification import SkillEffectKind
from models.build_model import PlayerBuild
from tools.audit_phase12_saved_build_candidates import (
    _candidate_change_label,
    _select_verified_healing_skills,
    _with_extra_unresolved,
)


class _Coefficients:
    def resolve_name(self, name):
        if name == "Missing":
            return SimpleNamespace(rank=None, unresolved=("Skill name not found",))
        rank_id = {
            "Heal": 1,
            "Damage": 2,
            "Unknown": 3,
        }[name]
        return SimpleNamespace(rank=SimpleNamespace(skill_rank_id=rank_id), unresolved=())


class _Components:
    def get_for_skill_rank(self, skill_rank_id):
        if skill_rank_id == 1:
            return (SimpleNamespace(effect_kind=SkillEffectKind.HEAL),)
        if skill_rank_id == 2:
            return (SimpleNamespace(effect_kind=SkillEffectKind.DAMAGE),)
        if skill_rank_id == 3:
            return (SimpleNamespace(effect_kind=SkillEffectKind.UNKNOWN),)
        return ()


class _TooltipService:
    def __init__(self):
        self.coefficients = _Coefficients()
        self.components = _Components()


def test_audit_skill_selection_includes_only_verified_heals() -> None:
    selected, excluded, unresolved = _select_verified_healing_skills(
        ("Heal", "Damage", "Unknown", "Missing"),
        _TooltipService(),
    )

    assert selected == ("Heal",)
    assert excluded == ("Damage",)
    assert unresolved == (
        "Unknown: effect kind unresolved for one or more components",
        "Missing: Skill name not found",
    )


def test_audit_skill_selection_unresolved_evidence_blocks_baseline_metric() -> None:
    result = ModeledHealingPotency(
        value=123.0,
        evaluated_skills=("Heal",),
        evidence=("heal evidence",),
    )

    updated = _with_extra_unresolved(result, ("Unknown: effect kind unresolved",))

    assert updated.value == 123.0
    assert updated.unresolved == ("Unknown: effect kind unresolved",)
    assert updated.resolved is False


def _comparison(path: str, before: str, after: str) -> BuildCandidateComparison:
    build = PlayerBuild(Name="Magrat", BuildName="DF Healer", Mundus="The Ritual")
    candidate = BuildCandidate.from_build(
        character_id="magrat",
        baseline_build_id="DF Healer",
        candidate_id="candidate",
        candidate_build=build,
        changes=(
            BuildChange.from_values(
                path=path,
                before=before,
                after=after,
                source="test",
            ),
        ),
        candidate_source="test",
    )
    return BuildCandidateComparison(
        candidate=candidate,
        objective=EvaluationObjective.HEALING,
        baseline_value=100.0,
        candidate_value=101.0,
        constraints=(),
    )


def test_audit_candidate_labels_keep_families_explainable() -> None:
    assert _candidate_change_label(
        _comparison("Mundus", "The Ritual", "The Mage")
    ) == "The Mage"
    assert _candidate_change_label(
        _comparison("Armor.Shoulders.Trait", "Infused", "Divines")
    ) == "Armor.Shoulders.Trait: Infused -> Divines"
