from minmax.combat_state_snapshot import CombatStateSnapshot, CombatantSnapshot
from minmax.runtime_effect_window import RuntimeEffectActiveWindow
from minmax.character_build.effect_instance import EffectVariant
from minmax.support_effect_category import SupportEffectCategory
from minmax.runtime_event import RuntimeEvent
from minmax.runtime_effect_eligibility import RuntimeEffectState
from minmax.resource_state import StaticResourceState, StaticResourcePool
from minmax.resource_costs import ResourceType

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


def test_projects_status_only_with_canonical_effect_metadata():
 w=RuntimeEffectActiveWindow("burning","skill",0,10,target="boss")
 e=EffectVariant(name="burning",layer=None,source="skill",category=SupportEffectCategory.STATUS)
 state=CombatStateSnapshot.from_windows(1,CombatantSnapshot("player"),(w,),effects=(e,))
 assert state.active_statuses("boss")[0].name == "burning"

def test_known_self_buff_bridges_to_static_combat_state():
 w=RuntimeEffectActiveWindow("Major Courage","skill",0,10)
 e=EffectVariant(name="Major Courage",layer=None,source="skill",category=SupportEffectCategory.BUFF)
 state=CombatStateSnapshot.from_windows(1,CombatantSnapshot("player"),(w,),effects=(e,))
 assert state.static_combat_state().has_buff("Major Courage")

def test_snapshot_delegates_cooldown_eligibility_to_phase7():
 effect=EffectVariant(name="proc",layer=None,source="skill",trigger="cast",cooldown=10)
 event=RuntimeEvent(5,"cast","skill")
 state=CombatStateSnapshot(5,CombatantSnapshot("player"))
 assert not state.eligibility(event,effect,RuntimeEffectState(last_activation_time_seconds=0)).eligible

def test_combatant_uses_phase4_static_resource_capacities():
 resources=StaticResourceState(StaticResourcePool(ResourceType.HEALTH,100,0),StaticResourcePool(ResourceType.MAGICKA,200,0),StaticResourcePool(ResourceType.STAMINA,300,0))
 player=CombatantSnapshot.from_static_resources("player",resources,current_health=50,current_magicka=100)
 assert (player.maximum_health,player.maximum_magicka,player.maximum_stamina)==(100,200,300)

def test_reports_retained_runtime_instances_without_claiming_stack_semantics():
 windows=(RuntimeEffectActiveWindow("dot","skill",0,10,target="boss"),RuntimeEffectActiveWindow("dot","skill",1,10,target="boss"))
 effect=EffectVariant(name="dot",layer=None,source="skill")
 state=CombatStateSnapshot.from_windows(2,CombatantSnapshot("player"),windows,effects=(effect,))
 assert state.active_instance_count("dot","boss")==2
