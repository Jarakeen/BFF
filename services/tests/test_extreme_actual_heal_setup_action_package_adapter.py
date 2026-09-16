from minmax.build_candidate import BuildCandidate, BuildChange
from models.build_model import PlayerBuild
from services.extreme_actual_heal_setup_action_legality_service import (
    HAS_CAST_OR_CHANNEL_TIME,
    IS_ARMOR_ABILITY,
    ExtremeActualHealSetupActionWitness,
)
from services.extreme_actual_heal_setup_action_package_adapter import (
    ExtremeActualHealSetupActionPackageAdapter,
)


class _Delegate:
    def __init__(self, candidate: BuildCandidate) -> None:
        self.candidate = candidate

    def build_candidates(self, *args, **kwargs):
        return (self.candidate,)


class _Legality:
    def witness(self, capability, context):
        skill = "Magicka Detonation" if capability == HAS_CAST_OR_CHANNEL_TIME else "Vigor"
        return ExtremeActualHealSetupActionWitness(
            capability=capability,
            skill_name=skill,
            skill_line="Assault",
            ability_id=12345,
            evidence=f"{skill} setup witness",
        )


def _candidate(set_name: str = "Seventh Legion Brute", candidate_id: str = "seventh") -> BuildCandidate:
    build = PlayerBuild()
    for slot in ("Head", "Chest", "Legs", "Shoulders", "Hands"):
        build.Armor[slot]["Set"] = set_name
    build.FrontBarSkills = ["Scored Heal", "A", "B", "C", "D", "Front Ultimate"]
    build.BackBarSkills = ["One", "Two", "Three", "Four", "Five", "Back Ultimate"]
    return BuildCandidate.from_build(
        character_id="char",
        baseline_build_id="base",
        candidate_id=candidate_id,
        candidate_build=build,
        changes=(BuildChange.from_values(path="Armor", before="baseline", after=set_name, source="test"),),
        candidate_source="test",
    )


def test_seventh_legion_candidate_expands_all_full_inactive_bar_resolve_placements() -> None:
    adapter = ExtremeActualHealSetupActionPackageAdapter(_Delegate(_candidate()), _Legality())
    rows = adapter.build_candidates(PlayerBuild(), active_bar="front")
    setup = tuple(row for row in rows if ":setup-resolve:" in row.candidate_id)
    assert len(setup) == 5
    assert rows[0].candidate_id == "seventh"
    assert {row.candidate_id.rsplit(":", 1)[-1] for row in setup} == {"0", "1", "2", "3", "4"}
    assert all(row.candidate_build.FrontBarSkills[0] == "Scored Heal" for row in setup)
    assert all(row.candidate_build.FrontBarSkills[5] == "Front Ultimate" for row in setup)
    assert all(row.candidate_build.BackBarSkills[5] == "Back Ultimate" for row in setup)
    assert all("Vigor" in row.candidate_build.BackBarSkills[:5] for row in setup)


def test_soulshine_candidate_reuses_same_inactive_bar_frontier_with_cast_channel_witness() -> None:
    adapter = ExtremeActualHealSetupActionPackageAdapter(
        _Delegate(_candidate("Soulshine", "soulshine")),
        _Legality(),
    )
    rows = adapter.build_candidates(PlayerBuild(), active_bar="front")
    setup = tuple(row for row in rows if ":setup-cast-channel:" in row.candidate_id)
    assert len(setup) == 5
    assert all("Magicka Detonation" in row.candidate_build.BackBarSkills[:5] for row in setup)
    assert all(row.candidate_build.FrontBarSkills[0] == "Scored Heal" for row in setup)
    assert all(row.candidate_build.BackBarSkills[5] == "Back Ultimate" for row in setup)


def test_unreviewed_set_is_not_setup_expanded() -> None:
    ordinary = _candidate("Other Set", "ordinary")
    adapter = ExtremeActualHealSetupActionPackageAdapter(_Delegate(ordinary), _Legality())
    rows = adapter.build_candidates(PlayerBuild(), active_bar="front")
    assert [row.candidate_id for row in rows] == ["ordinary"]

def test_armor_master_materializes_armor_ability_on_scored_active_bar() -> None:
    candidate = _candidate("Armor Master", "armor-master")
    for entry in candidate.candidate_build.Armor.values():
        entry["Weight"] = "Light"
    adapter = ExtremeActualHealSetupActionPackageAdapter(_Delegate(candidate), _Legality())

    rows = adapter.build_candidates(PlayerBuild(), active_bar="front")

    slotted = tuple(row for row in rows if ":setup-armor-ability-slotted:" in row.candidate_id)
    assert len(slotted) == 5
    assert all("Vigor" in row.candidate_build.FrontBarSkills[:5] for row in slotted)
    assert all(row.candidate_build.BackBarSkills == candidate.candidate_build.BackBarSkills for row in slotted)

