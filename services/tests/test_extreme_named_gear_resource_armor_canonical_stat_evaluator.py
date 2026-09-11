from dataclasses import replace
from types import SimpleNamespace

from models.build_model import PlayerBuild
from services.extreme_armor_resource_trait_glyph_state_service import (
    ExtremeArmorResourceTraitGlyphPieceChoice,
    ExtremeArmorResourceTraitGlyphState,
)
from services.extreme_armor_resource_weight_state_service import (
    ExtremeArmorResourceWeightState,
)
from services.extreme_armor_resource_weight_trait_glyph_state_service import (
    ExtremeArmorResourceWeightTraitGlyphState,
)
from services.extreme_named_gear_resource_armor_canonical_stat_evaluator import (
    ExtremeNamedGearResourceArmorCanonicalStatEvaluator,
)
from services.extreme_resource_active_bar_state_service import (
    ExtremeResourceActiveBarState,
)


class _ProgressionService:
    def normalize(self, progression, route):
        return progression


class _ResourceArmorProgressionService:
    def normalize(self, progression, route):
        ranks = dict(progression.passive_ranks or {})
        ranks["Juggernaut"] = 2
        return replace(
            progression,
            owned_skill_lines=tuple(dict.fromkeys((*progression.owned_skill_lines, "Heavy Armor"))),
            passive_ranks=ranks,
        )


class _ActiveBarProgressionService:
    def normalize(self, progression, route):
        ranks = dict(progression.passive_ranks or {})
        ranks["Magicka Controller"] = 2
        return replace(
            progression,
            owned_skill_lines=tuple(dict.fromkeys((*progression.owned_skill_lines, "Mages Guild"))),
            passive_ranks=ranks,
        )


class _ActiveBarStateService:
    state = ExtremeResourceActiveBarState(
        objective_key="max_magicka",
        skills=(
            "Siphoning Skill",
            "Mages 1",
            "Mages 2",
            "Mages 3",
            "Mages 4",
            "Mages Ultimate",
        ),
        siphoning_slots=1,
        mages_guild_slots=5,
        reviewed_percent_bonus=0.16,
    )

    def build(self, objective_key, route):
        assert objective_key == "max_magicka"
        return SimpleNamespace(
            states=(self.state,),
            denominator_proven=True,
            active_skills_reviewed=42,
            unresolved=(),
        )

    @staticmethod
    def materialize(build, state, *, active_bar):
        result = PlayerBuild.from_dict(build.to_dict())
        if active_bar == "back":
            result.BackBarSkills = list(state.skills)
        else:
            result.FrontBarSkills = list(state.skills)
        return result


class _RacialProgressionService:
    def normalize(self, progression, race):
        ranks = dict(progression.passive_ranks or {})
        ranks["Syrabane's Boon"] = 3
        return replace(
            progression,
            owned_skill_lines=tuple(dict.fromkeys((*progression.owned_skill_lines, "High Elf Skills"))),
            passive_ranks=ranks,
        )


class _Optimizer:
    def __init__(self):
        self.last_build = None

    def objective(self, key):
        return SimpleNamespace(key=key)

    def _evaluate(self, build, **kwargs):
        self.last_build = build
        return 1234.0, ()

    def _objective_value(self, context, objective):
        return context.value


class _ContextFactory:
    def __init__(self):
        self.last_progression = None
        self.last_build = None

    def build(self, *, build, progression, **kwargs):
        self.last_build = build
        self.last_progression = progression
        return SimpleNamespace(value=4321.0, unresolved_gear_effects=())


class _NamedGearEvaluator:
    def __init__(self):
        self.optimizer = _Optimizer()
        self.progression_service = _ProgressionService()

    def evaluate_candidate(self, objective_key, candidate, **kwargs):
        build = PlayerBuild()
        build.Race = candidate.race
        build.Armor["Head"]["Set"] = "Set A"
        build.Armor["Chest"]["Set"] = "Set B"
        return 100.0, {"build": build.to_dict(), "gear_set_names": ("Set A", "Set B")}, ()


def _candidate(race="Nord"):
    return SimpleNamespace(
        race=race,
        attributes=SimpleNamespace(health=64, magicka=0, stamina=0),
        class_route=SimpleNamespace(),
        active_bar="front",
        identity=(race, "Dragonknight", (), 64, 0, 0, "front"),
    )


def _state(objective="max_health"):
    slots = ("Head", "Shoulders", "Chest", "Hands", "Waist", "Legs", "Feet")
    pieces = tuple(
        ExtremeArmorResourceTraitGlyphPieceChoice(
            slot=slot,
            trait="Infused" if slot == "Chest" else "Divines",
            enchant="Max Health",
            direct_delta=100.0,
        )
        for slot in slots
    )
    trait_glyph = ExtremeArmorResourceTraitGlyphState(
        objective_key=objective,
        pieces=pieces,
        direct_glyph_delta=700.0,
    )
    weights = tuple(
        (slot, "Heavy" if slot == "Chest" else ("Medium" if slot == "Hands" else "Light"))
        for slot in slots
    )
    weight = ExtremeArmorResourceWeightState(
        objective_key=objective,
        weights=weights,
    )
    return ExtremeArmorResourceWeightTraitGlyphState(
        objective_key=objective,
        weight_state=weight,
        trait_glyph_state=trait_glyph,
    )


def test_combined_evaluator_preserves_sets_and_scores_materialized_resource_armor():
    named = _NamedGearEvaluator()
    evaluator = ExtremeNamedGearResourceArmorCanonicalStatEvaluator(
        evaluator=named,
        armor_state=_state(),
    )

    value, payload, unresolved = evaluator.evaluate_candidate("max_health", _candidate())

    assert value == 1234.0
    assert unresolved == ()
    build = named.optimizer.last_build
    assert build.Armor["Head"]["Set"] == "Set A"
    assert build.Armor["Chest"]["Set"] == "Set B"
    assert build.Armor["Chest"]["Weight"] == "Heavy"
    assert build.Armor["Hands"]["Weight"] == "Medium"
    assert build.Armor["Head"]["Weight"] == "Light"
    assert build.Armor["Chest"]["Trait"] == "Infused"
    assert build.Armor["Chest"]["Enchant"] == "Max Health"
    assert build.Armor["Chest"]["Quality"] == "Gold"
    assert build.Armor["Chest"]["Level"] == "CP160"
    assert build.Armor["Chest"]["EnchantTier"] == "Truly Superb"
    assert payload["armor_type_count"] == 3
    assert payload["armor_infused_count"] == 1
    assert payload["armor_divines_count"] == 6
    assert payload["armor_reviewed_glyph_delta"] == 700.0


def test_resource_evaluator_applies_hypothetical_racial_progression_to_canonical_context():
    named = _NamedGearEvaluator()
    context_factory = _ContextFactory()
    evaluator = ExtremeNamedGearResourceArmorCanonicalStatEvaluator(
        evaluator=named,
        armor_state=_state("max_magicka"),
        racial_progression_service=_RacialProgressionService(),
        context_factory=context_factory,
    )

    value, payload, unresolved = evaluator.evaluate_candidate(
        "max_magicka",
        _candidate("High Elf"),
    )

    assert value == 4321.0
    assert unresolved == ()
    assert context_factory.last_build.Race == "High Elf"
    assert context_factory.last_progression.passive_rank("Syrabane's Boon") == 3
    assert context_factory.last_progression.owns_skill_line("High Elf Skills") is True
    assert payload["racial_progression_applied"] is True


def test_resource_evaluator_applies_juggernaut_progression_to_canonical_context():
    named = _NamedGearEvaluator()
    context_factory = _ContextFactory()
    evaluator = ExtremeNamedGearResourceArmorCanonicalStatEvaluator(
        evaluator=named,
        armor_state=_state("max_health"),
        resource_armor_progression_service=_ResourceArmorProgressionService(),
        context_factory=context_factory,
    )

    value, payload, unresolved = evaluator.evaluate_candidate("max_health", _candidate())

    assert value == 4321.0
    assert unresolved == ()
    assert context_factory.last_progression.owns_skill_line("Heavy Armor") is True
    assert context_factory.last_progression.passive_rank("Juggernaut") == 2
    assert payload["juggernaut_rank"] == 2
    assert payload["juggernaut_progression_applied"] is True


def test_resource_evaluator_materializes_reviewed_bar_and_progression_into_same_context():
    named = _NamedGearEvaluator()
    context_factory = _ContextFactory()
    evaluator = ExtremeNamedGearResourceArmorCanonicalStatEvaluator(
        evaluator=named,
        armor_state=_state("max_magicka"),
        active_bar_progression_service=_ActiveBarProgressionService(),
        active_bar_state_service=_ActiveBarStateService(),
        context_factory=context_factory,
    )

    value, payload, unresolved = evaluator.evaluate_candidate("max_magicka", _candidate())

    assert value == 4321.0
    assert unresolved == ()
    assert tuple(context_factory.last_build.FrontBarSkills) == _ActiveBarStateService.state.skills
    assert context_factory.last_progression.owns_skill_line("Mages Guild") is True
    assert context_factory.last_progression.passive_rank("Magicka Controller") == 2
    assert payload["resource_active_bar_siphoning_slots"] == 1
    assert payload["resource_active_bar_mages_guild_slots"] == 5
    assert payload["resource_active_bar_reviewed_percent_bonus"] == 0.16
    assert payload["resource_active_bar_denominator_proven"] is True
    assert payload["magicka_controller_progression_applied"] is True


def test_objective_mismatch_fails_closed():
    evaluator = ExtremeNamedGearResourceArmorCanonicalStatEvaluator(
        evaluator=_NamedGearEvaluator(),
        armor_state=_state("max_health"),
    )

    try:
        evaluator.evaluate_candidate("max_magicka", _candidate())
    except ValueError as exc:
        assert "objective mismatch" in str(exc)
    else:
        raise AssertionError("expected resource armor objective mismatch to fail closed")
