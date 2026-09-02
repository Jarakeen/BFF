from __future__ import annotations
import argparse
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from engine.config import DEFAULT_DATABASE,get_data_dir
from minmax.context_factory import BuildCalculationContextFactory
from minmax.gear_set_repository import GearSetRepository
from minmax.race_repository import RaceRepository
from minmax.resource_state import StaticResourceState
from minmax.combat_state_snapshot import CombatantSnapshot,CombatStateSnapshot
from tools.audit_phase4_saved_build_sustain import _audit_progression,_find_build,_load_saved_builds
def main():
 p=argparse.ArgumentParser();p.add_argument("--database",type=Path,default=DEFAULT_DATABASE);p.add_argument("--builds",type=Path,default=get_data_dir()/"builds.json");p.add_argument("--build",default="DF Healer");p.add_argument("--active-bar",default="front");a=p.parse_args()
 b=_find_build(_load_saved_builds(a.builds),a.build);ctx=BuildCalculationContextFactory(race_repository=RaceRepository(a.database),gear_set_repository=GearSetRepository(a.database)).build(character_id=b.Name or "saved-character",build_id=b.BuildName,build=b,progression=_audit_progression(b),active_bar=a.active_bar)
 player=CombatantSnapshot.from_static_resources(b.Name or "player",StaticResourceState.from_base_character_state(ctx.character_state))
 snap=CombatStateSnapshot(0,player)
 print("PHASE 8 SAVED-BUILD SNAPSHOT AUDIT");print(f"Build: {b.BuildName}");print(f"Health/Magicka/Stamina: {player.maximum_health}/{player.maximum_magicka}/{player.maximum_stamina}");print(f"Snapshot time: {snap.time_seconds}");print("Caller inputs still required: current resources, runtime event history, target state, position/range, encounter phase");return 0
if __name__=="__main__": raise SystemExit(main())
