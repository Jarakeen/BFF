from minmax.combat_state_snapshot import CombatStateSnapshot, CombatantSnapshot
from minmax.runtime_effect_window import RuntimeEffectActiveWindow

def test_projects_active_windows_with_end_exclusive_boundary():
    window=RuntimeEffectActiveWindow("Major Courage","Potion",0,10)
    player=CombatantSnapshot("player",50,100)
    assert CombatStateSnapshot.from_windows(9.999,player,(window,)).active_windows == (window,)
    assert CombatStateSnapshot.from_windows(10,player,(window,)).active_windows == ()

def test_health_threshold_is_explicit_or_unknown():
    assert CombatStateSnapshot(0,CombatantSnapshot("player",24,100)).meets_health_threshold(.25) is True
    assert CombatStateSnapshot(0,CombatantSnapshot("player",25,100)).meets_health_threshold(.25) is False
    assert CombatStateSnapshot(0,CombatantSnapshot("player",None,100)).meets_health_threshold(.25) is None


def test_target_execute_truth_and_validation():
    boss=CombatantSnapshot("boss",24,100,current_magicka=0,maximum_magicka=1)
    state=CombatStateSnapshot(0,CombatantSnapshot("player"),targets=(boss,))
    assert state.meets_health_threshold(.25,"boss") is True
    assert state.meets_health_threshold(.25,"missing") is None

