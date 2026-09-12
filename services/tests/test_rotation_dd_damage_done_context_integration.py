from types import SimpleNamespace

from minmax.base_character_state import BaseCharacterState
from minmax.build_calculation_context import BuildCalculationContext
from minmax.character_progression import CharacterProgression
from minmax.combat_state import CombatState
from minmax.damage_done import DamageDoneModifiers, resolve_damage_done
from models.build_model import PlayerBuild
from services.minmax_character_progression_adapter import SavedBuildProgressionResolution
from services.rotation_candidate_skill_damage_evidence_service import (
    RotationCandidateSkillDamageEvidenceService,
)
from services.rotation_saved_build_dd_damage_done_service import (
    RotationSavedBuildDDDamageDoneResolution,
)
from services.rotation_static_build_context_service import RotationStaticBuildContextService


class _ProgressionAdapter:
    def resolve(self, _build):
        return SavedBuildProgressionResolution(
            character_id="ryl-1",
            progression=CharacterProgression(passive_ranks={}, passive_cp_points={}),
            unresolved=(),
        )


class _ContextFactory:
    def build(self, **kwargs):
        return BuildCalculationContext(
            character_id=kwargs["character_id"],
            build_id=kwargs["build_id"],
            progression=kwargs["progression"],
            character_state=BaseCharacterState(
                max_health=20000,
                max_magicka=30000,
                max_stamina=30000,
                health_recovery=500,
                magicka_recovery=1500,
                stamina_recovery=1500,
                traces={},
            ),
            combat_state=kwargs["combat_state"],
            active_bar=kwargs["active_bar"],
        )


class _DDDamageDoneService:
    def __init__(self, *, modifiers, unresolved=()):
        self.modifiers = modifiers
        self.unresolved = tuple(unresolved)
        self.calls = []

    def resolve(self, build):
        self.calls.append(build)
        return RotationSavedBuildDDDamageDoneResolution(
            modifiers=self.modifiers,
            unresolved=self.unresolved,
        )


def test_dd_static_context_carries_reviewed_unconditional_damage_done() -> None:
    modifiers = DamageDoneModifiers(direct=0.06, area=0.06, dot=0.03)
    dd_service = _DDDamageDoneService(modifiers=modifiers)
    service = RotationStaticBuildContextService(
        progression_adapter=_ProgressionAdapter(),
        context_factory=_ContextFactory(),
        dd_damage_done_service=dd_service,  # type: ignore[arg-type]
    )
    build = PlayerBuild(Name="Rylonia", BuildName="Corpsebuster DD", Role="DD")

    result = service.resolve(build)

    assert result.resolved is True
    assert dd_service.calls == [build]
    assert [context.dd_damage_done_modifiers for context in result.contexts] == [
        modifiers,
        modifiers,
    ]


def test_dd_damage_done_resolution_failure_remains_fail_closed() -> None:
    dd_service = _DDDamageDoneService(
        modifiers=DamageDoneModifiers(),
        unresolved=("Champion Point Biting Aura: reviewed DD semantics unavailable",),
    )
    service = RotationStaticBuildContextService(
        progression_adapter=_ProgressionAdapter(),
        context_factory=_ContextFactory(),
        dd_damage_done_service=dd_service,  # type: ignore[arg-type]
    )

    result = service.resolve(
        PlayerBuild(Name="Rylonia", BuildName="Corpsebuster DD", Role="DD")
    )

    assert result.resolved is False
    assert result.unresolved == (
        "Champion Point Biting Aura: reviewed DD semantics unavailable",
    )


def test_skill_damage_uses_cp_categories_without_cross_contamination() -> None:
    context = BuildCalculationContext(
        character_id="ryl-1",
        build_id="corpsebuster",
        progression=CharacterProgression(),
        character_state=BaseCharacterState(
            max_health=20000,
            max_magicka=30000,
            max_stamina=30000,
            health_recovery=500,
            magicka_recovery=1500,
            stamina_recovery=1500,
            traces={},
        ),
        combat_state=CombatState(active_buffs=("Major Berserk",)),
        dd_damage_done_modifiers=DamageDoneModifiers(
            direct=0.06,
            area=0.06,
            dot=0.03,
        ),
    )

    merged = RotationCandidateSkillDamageEvidenceService._damage_done_for_context(context)
    direct_aoe = resolve_damage_done(
        merged,
        damage_type="magical",
        is_dot=False,
        is_aoe=True,
    )
    dot_single_target = resolve_damage_done(
        merged,
        damage_type="magical",
        is_dot=True,
        is_aoe=False,
    )

    assert direct_aoe.generic == 0.10
    assert direct_aoe.delivery == 0.06
    assert direct_aoe.target_shape == 0.06
    assert direct_aoe.total == 0.22

    assert dot_single_target.generic == 0.10
    assert dot_single_target.delivery == 0.03
    assert dot_single_target.target_shape == 0.0
    assert dot_single_target.total == 0.13
