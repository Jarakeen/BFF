from types import SimpleNamespace

from models.build_model import PlayerBuild

from minmax.build_candidate_healing import measure_modeled_healing_potency
from minmax.skill_component_classification import SkillEffectKind


class _Coefficients:
    def resolve_name(self, name):
        if name == "Missing Skill":
            return SimpleNamespace(rank=None, unresolved=("Skill name not found",))
        return SimpleNamespace(
            rank=SimpleNamespace(entity_id=name.casefold().replace(" ", "_")),
            unresolved=(),
        )


class _Components:
    def __init__(self, classifications):
        self.classifications = classifications

    def get_for_skill_rank(self, skill_rank_id):
        return self.classifications[skill_rank_id]


class _TooltipService:
    def __init__(self, results, classifications):
        self.coefficients = _Coefficients()
        self.components = _Components(classifications)
        self.results = results
        self.calls = []

    def evaluate_entity_id(self, *, build, context, entity_id):
        self.calls.append((build, context, entity_id))
        return self.results[entity_id]


def _classification(number, kind):
    return SimpleNamespace(coefficient_number=number, effect_kind=kind)


def _result(
    *,
    name="Healing Skill",
    rank_id=10,
    components=(),
    actual=(),
    unresolved=(),
):
    return SimpleNamespace(
        skill=SimpleNamespace(
            name=name,
            entity_id=name.casefold().replace(" ", "_"),
            skill_rank_id=rank_id,
        ),
        components=components,
        component_actual_effect_trace=actual,
        unresolved=unresolved,
    )


def test_modeled_healing_potency_sums_only_verified_heal_components() -> None:
    result = _result(
        components=(
            SimpleNamespace(coefficient_number=1, final_value=1000.0),
            SimpleNamespace(coefficient_number=2, final_value=5000.0),
            SimpleNamespace(coefficient_number=3, final_value=2000.0),
        ),
        actual=(
            SimpleNamespace(coefficient_number=1, output_value=1080.0),
            SimpleNamespace(coefficient_number=3, output_value=2160.0),
        ),
    )
    service = _TooltipService(
        {"healing_skill": result},
        {
            10: (
                _classification(1, SkillEffectKind.HEAL),
                _classification(2, SkillEffectKind.DAMAGE),
                _classification(3, SkillEffectKind.HEAL),
            )
        },
    )

    measured = measure_modeled_healing_potency(
        build=PlayerBuild(),
        context=object(),
        skill_names=("Healing Skill",),
        tooltip_service=service,
    )

    assert measured.resolved
    assert measured.value == 3240.0
    assert len(measured.evidence) == 2
    assert all("modeled heal" in row for row in measured.evidence)


def test_modeled_healing_potency_deduplicates_selected_skill_names() -> None:
    result = _result(
        components=(SimpleNamespace(coefficient_number=1, final_value=1000.0),),
    )
    service = _TooltipService(
        {"healing_skill": result},
        {10: (_classification(1, SkillEffectKind.HEAL),)},
    )

    measured = measure_modeled_healing_potency(
        build=PlayerBuild(),
        context=object(),
        skill_names=("Healing Skill", "healing skill", "Healing Skill"),
        tooltip_service=service,
    )

    assert measured.value == 1000.0
    assert len(service.calls) == 1


def test_modeled_healing_potency_keeps_unknown_component_kind_unresolved() -> None:
    result = _result(
        components=(
            SimpleNamespace(coefficient_number=1, final_value=1000.0),
            SimpleNamespace(coefficient_number=2, final_value=500.0),
        ),
    )
    service = _TooltipService(
        {"healing_skill": result},
        {
            10: (
                _classification(1, SkillEffectKind.HEAL),
                _classification(2, SkillEffectKind.UNKNOWN),
            )
        },
    )

    measured = measure_modeled_healing_potency(
        build=PlayerBuild(),
        context=object(),
        skill_names=("Healing Skill",),
        tooltip_service=service,
    )

    assert measured.value == 1000.0
    assert not measured.resolved
    assert any("effect kind unresolved" in row for row in measured.unresolved)


def test_modeled_healing_potency_keeps_tooltip_unresolved_evidence() -> None:
    result = _result(
        components=(SimpleNamespace(coefficient_number=1, final_value=1000.0),),
        unresolved=("unsupported coefficient type 12",),
    )
    service = _TooltipService(
        {"healing_skill": result},
        {10: (_classification(1, SkillEffectKind.HEAL),)},
    )

    measured = measure_modeled_healing_potency(
        build=PlayerBuild(),
        context=object(),
        skill_names=("Healing Skill",),
        tooltip_service=service,
    )

    assert measured.value == 1000.0
    assert not measured.resolved
    assert "Healing Skill: unsupported coefficient type 12" in measured.unresolved


def test_modeled_healing_potency_rejects_empty_or_unresolvable_selection() -> None:
    service = _TooltipService({}, {})

    empty = measure_modeled_healing_potency(
        build=PlayerBuild(),
        context=object(),
        skill_names=(),
        tooltip_service=service,
    )
    missing = measure_modeled_healing_potency(
        build=PlayerBuild(),
        context=object(),
        skill_names=("Missing Skill",),
        tooltip_service=service,
    )

    assert empty.value is None
    assert not empty.resolved
    assert missing.value is None
    assert not missing.resolved
    assert any("Skill name not found" in row for row in missing.unresolved)
