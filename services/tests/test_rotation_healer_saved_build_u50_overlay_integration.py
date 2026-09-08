from types import SimpleNamespace

from models.build_model import PlayerBuild
from services.rotation_healer_saved_build_periodic_timing_service import (
    RotationHealerSavedBuildPeriodicTimingService,
)
from services.rotation_healer_u50_skill_component_repository import (
    RotationHealerU50SkillComponentRepository,
)


class _Coefficients:
    def resolve_name(self, name):
        if name == "Budding Seeds":
            return SimpleNamespace(
                rank=SimpleNamespace(
                    skill_rank_id=RotationHealerU50SkillComponentRepository.BUDDING_SEEDS_RANK_ID
                ),
                unresolved=(),
            )
        return SimpleNamespace(rank=None, unresolved=("not used",))


class _Timing:
    def resolve(self, *, source_name, coefficient_number):
        return SimpleNamespace(
            source_name=source_name,
            coefficient_number=coefficient_number,
            unresolved=(),
        )


def test_default_u50_overlay_discovers_budding_seeds_field_hot_only():
    build = PlayerBuild(
        Name="Magrat",
        BuildName="DF Healer",
        FrontBarSkills=["Budding Seeds", "", "", "", "", ""],
    )
    service = RotationHealerSavedBuildPeriodicTimingService(
        "missing.db",
        coefficient_repository=_Coefficients(),
        timing_service=_Timing(),
    )

    report = service.inspect(build)

    assert report.unresolved == ()
    assert len(report.entries) == 1
    entry = report.entries[0]
    assert entry.bar == "front"
    assert entry.slot == 1
    assert entry.skill_name == "Budding Seeds"
    assert entry.coefficient_number == 2
