# engine/import.py
import os
import json
import requests

# 1. Set the UESP JSON export API URL for equippable armor
url = "esolog.uesp.net/exportJson.php?table=minedItemSummary&type=2"

# 2. Make the web request
print("Fetching armor data from UESP...")
response = requests.get(url)

if response.status_code == 200:
    # UESP returns a native JSON object automatically
    data = response.json()
    
    # 3. Extract just the list of items from the table element
    # The API nests records under a key matching the table name
    armor_records = data.get("minedItemSummary", [])
    
    # 4. Create the directory structure safely
    os.makedirs("game data", exist_ok=True)
    output_path = os.path.join("game data", "set.json")
    
    # 5. Save the data to your file
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(armor_records, f, indent=4, ensure_ascii=False)
        
    print(f"Successfully saved {data.get('numRecords', 0)} armor items to {output_path}!")
else:
    print(f"Failed to fetch data from UESP. Status code: {response.status_code}")