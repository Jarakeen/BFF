import time
import threading
import json
import customtkinter as ctk
from pathlib import Path 

# Initialize the path tracking layer right here:
CURRENT_DIR = Path(__file__).resolve().parent

# Place this directly inside your standard App class in console/engine/sorce/desktop_gui.py
def load_saved_roster_data(self, roster_file_name: str = "roster.json"):
    """Reads saved Xbox player layout files and loads profiles into the configurator."""
    # 1. CURRENT_DIR references your updated 'sorce' path framework
    # 2. Walk backwards up to console/, then dive into game_data/eso/
    roster_path = CURRENT_DIR.parent.parent / "game_data" / "eso" / roster_file_name
    
    if not roster_path.exists():
        self.directives_box.insert("1.0", f"[SYSTEM ALERT]: {roster_file_name} not found in database path.")
        return

    with open(roster_path, "r", encoding="utf-8") as f:
        roster_data = json.load(f)

    # 3. Process configuration injection maps into your dropdown options elements
    for player_profile in roster_data.get("roster", []):
        gamertag = player_profile["gamertag"]
        role = player_profile["role"]
        
        # Resolve which slot this profile targets in your layout grid view matrix
        for label_name, (role_type, dropdown) in self.roster_inputs.items():
            if role_type == role and dropdown.get() == "Empty":
                equipped = player_profile["choices"]["equipped_gear_sets"]
                
                if "Turning Tide" in equipped:
                    dropdown.set("Meta Pierce Armor Setup")
                elif "Spell Power Cure" in equipped:
                    dropdown.set("Spell Power Cure Setup")
                break




class XboxFightClock:
    def __init__(self, ui_update_callback):
        self.ui_callback = ui_update_callback
        self.is_running = False
        self.elapsed_seconds = 0.0
        self._thread = None

    def start_pull(self):
        """Triggered instantly when clicking your master 'PULL READY' desktop bar."""
        self.is_running = True
        self.elapsed_seconds = 0.0
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop_or_wipe(self):
        """Resets timers immediately on group wipe callouts."""
        self.is_running = False

    def _run_loop(self):
        while self.is_running:
            time.sleep(0.1) # Ticks exactly every 100ms to mirror game client updates
            self.elapsed_seconds += 0.1
            # Push the updated second metrics directly to the desktop dashboard UI thread
            self.ui_callback(round(self.elapsed_seconds, 1))

