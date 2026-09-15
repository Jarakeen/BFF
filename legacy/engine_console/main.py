# Legacy copy of the retired engine/main.py FastAPI prototype.
import os
import sys

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict

from engine.models import SourceGameObject, DynamicTrigger, CombatEffect
from legacy.engine_console.operations import TheConsoleOpsEngine
from pathlib import Path
from services.paths import PROCESSED

DATABASE_PATH = PROCESSED
ops_service = TheConsoleOpsEngine(data_directory_path=str(DATABASE_PATH))


app = FastAPI(
    title="The Console API",
    description="Raid operations engine for end-game ESO optimization.",
    version="1.0.0"
)


class RosterSelectionRequest(BaseModel):
    encounter_id: str
    roster_choices: Dict[str, List[dict]]


@app.get("/health")
def health_check():
    return {"status": "online", "engine": "The Console"}


@app.post("/operations/audit")
def perform_pre_fight_audit(payload: RosterSelectionRequest):
    try:
        report = ops_service.audit_raid_operations(
            roster_choices=payload.roster_choices,
            encounter_id=payload.encounter_id
        )
        return report
    except ValueError as val_err:
        raise HTTPException(status_code=404, detail=str(val_err))
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Engine runtime exception: {str(err)}")


def init_app_operations():
    return TheConsoleOpsEngine(data_directory_path=str(DATABASE_PATH))


if __name__ == "__main__":
    import uvicorn

    current_sorce_dir = os.path.dirname(os.path.abspath(__file__))
    engine_dir = os.path.dirname(current_sorce_dir)
    sys.path.insert(0, engine_dir)
    sys.path.insert(0, current_sorce_dir)
    os.chdir(engine_dir)
    uvicorn.run("sorce.main:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    from engine.engine import WeaponSwapSimulationEngine
    from engine.models import PredictiveHealerProfile, WeaponSetup

    finch_profile = PredictiveHealerProfile(
        gamertag="Finch",
        front_bar=WeaponSetup(weapon_type="Restoration Staff", enchantment="Absorb Magicka", trait="Powered"),
        back_bar=WeaponSetup(weapon_type="Ice Staff", enchantment="Frost Glyph", trait="Charged"),
        back_bar_dot_duration=12.0,
        back_bar_cast_time=1.5
    )

    sim = WeaponSwapSimulationEngine()
    analysis = sim.evaluate_minor_brittle_coverage(finch_profile)

    print("=== THE CONSOLE: DYNAMIC WEAPON SWAP SIMULATION ===")
    print(f"Target Identity Assessed: {finch_profile.gamertag}")
    print(f"Has Structural Capability to Brittle? -> {analysis['has_structural_capability']}")
    print(f"Predicted Group Uptime: {analysis['predicted_brittle_uptime_pct']}%")
    print(f"Raid Operations Clearance: Status = {analysis['is_reliable_coverage']}")
    print(f"Directive Callout: {analysis['operational_recommendation']}")


if __name__ == "__main__":
    from engine.data_miner import UESPSkillMiner

    DATA_PATH = str(PROCESSED)
    print("Initializing UESP Data Mining Pipeline...")
    miner = UESPSkillMiner(output_directory=DATA_PATH)
    log_output = miner.run_mining_pipeline()
    print(log_output)
