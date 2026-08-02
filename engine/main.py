import os
import sys

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict

# 1. Pull the real objects from your neighbor files
from models import SourceGameObject, DynamicTrigger, CombatEffect
from engine.operations import TheConsoleOpsEngine

# Inside console/engine/src/main.py
from pathlib import Path
from engine.operations import TheConsoleOpsEngine

# 1. Grab the folder where main.py lives: console/engine/src/
CURRENT_FILE_DIR = Path(__file__).resolve().parent

# 2. Walk backwards up 2 folder levels to reach the master root: console/
CONSOLE_ROOT_DIR = CURRENT_FILE_DIR.parent.parent

# 3. Dive straight forward into the parallel directory structure: console/game_data/eso/
DATABASE_PATH = CONSOLE_ROOT_DIR / "data" / "processed"

# 4. Bind the resolved absolute string path straight into your platform engine
ops_service = TheConsoleOpsEngine(data_directory_path=str(DATABASE_PATH))


app = FastAPI(
    title="The Console API",
    description="Raid operations engine for end-game ESO optimization.",
    version="1.0.0"
)

# --- REQUEST SCHEMAS (API Input Boundaries) ---
class RosterSelectionRequest(BaseModel):
    encounter_id: str
    # Maps a player's string name to a list of their chosen raw game item dictionaries
    roster_choices: Dict[str, List[dict]]

# --- ENDPOINTS ---
@app.get("/health")
def health_check():
    """Simple diagnostic verification ping."""
    return {"status": "online", "engine": "The Console"}

@app.post("/operations/audit")
def perform_pre_fight_audit(payload: RosterSelectionRequest):
    """
    Accepts incoming player choice vectors and audits capability sets 
    against Rylo's encounter requirements.
    """
    try:
        # Pass payload matrices cleanly through to your operations script
        report = ops_service.audit_raid_operations(
            roster_choices=payload.roster_choices,
            encounter_id=payload.encounter_id
        )
        return report
    except ValueError as val_err:
        raise HTTPException(status_code=404, detail=str(val_err))
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Engine runtime exception: {str(err)}")

from engine.operations import TheConsoleOpsEngine

def init_app_operations():
    # Points cleanly to your data directory structure
    ops_service = TheConsoleOpsEngine(data_directory_path=f"./{DATABASE_PATH}")
    return ops_service

# Replace the entire block at the bottom of console/engine/sorce/main.py with this:
if __name__ == "__main__":
    import uvicorn
    import os
    import sys

    # 1. Grab the folder path where main.py actually lives: console/engine/sorce/
    current_sorce_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 2. Grab the folder right above it: console/engine/
    engine_dir = os.path.dirname(current_sorce_dir)
    
    # 3. Explicitly append the actual 'sorce' path straight into Python's global root lookup array
    sys.path.insert(0, engine_dir)
    sys.path.insert(0, current_sorce_dir)
    os.chdir(engine_dir)

    # 4. Instruct Uvicorn to run from your exact 'sorce' folder layout
    uvicorn.run("sorce.main:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    from engine.engine import WeaponSwapSimulationEngine
    from models import PredictiveHealerProfile, WeaponSetup

    # Scenario: Finch runs a standard meta setup (Resto Front Bar / Ice Back Bar)
    finch_profile = PredictiveHealerProfile(
        gamertag="Finch",
        front_bar=WeaponSetup(weapon_type="Restoration Staff", enchantment="Absorb Magicka", trait="Powered"),
        # Testing with standard trait vs Charged trait optimization changes
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

# Add this testing snippet block to any execution file to run the database update
if __name__ == "__main__":
    from engine.data_miner import UESPSkillMiner
    import os

    # Set path directory straight to your parallel data folders
    DATA_PATH = "C:/Users/nourg/OneDrive/Desktop/Black Feather Foundry/40_Stream Studio/OBS/Scripts/FoundryDock/data/processed"
    
    print("Initializing UESP Data Mining Pipeline...")
    miner = UESPSkillMiner(output_directory=DATA_PATH)
    log_output = miner.run_mining_pipeline()
    print(log_output)


    