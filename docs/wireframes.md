# sidebar navigation
🪶 Black Feather Foundry

🏠 Dashboard

🎙 Operations

📋 Planning

🏆 Progression

📚 Archive

📖 Reference

⚙ Settings

# Dashboard
+----------------------------------------------------------------+
| Dashboard                                                      |
|================================================================|
| Active Expedition                      Recent Activity         |
|--------------------------------------------------------------- |
| Current Trial                           Recent Archives        |
| Current Objective                       Recent Incidents       |
| Expedition Status                       Recent Achievements    |
|                                                                |
|--------------------------------------------------------------- |
| Progress Snapshot                                              |
|--------------------------------------------------------------- |
| Achievement Completion                                         |
| Collection Completion                                          |
| Total Archives                                                 |
| Total Incidents                                                |
|                                                                |
|--------------------------------------------------------------- |
| Quick Actions                                                  |
| [ Start Expedition ] [ Open Current Run ] [ New Incident ]     |
+----------------------------------------------------------------+


# Operations
+----------------------------------------------------------------+
| Operations                                                     |
|================================================================|
| Broadcast | Current Run | Timers | Stream | Alerts             |
|----------------------------------------------------------------|
|                                                                |
| Main Workspace                                                 |
|                                                                |
|                                                                |
|                                                                |
|----------------------------------------------------------------|
| Status                                  Action Buttons         |
+----------------------------------------------------------------+


# Planning
+----------------------------------------------------------------+
| Planning                                                       |
|================================================================|
| Bosses | Composition | Assignments | Strategy                  |
|----------------------------------------------------------------|
|                                                                |
| Planning Workspace                                             |
|                                                                |
|                                                                |
|----------------------------------------------------------------|
| Status                                  Action Buttons         |
+----------------------------------------------------------------+

# Progression
+----------------------------------------------------------------+
| Progression                                                    |
|================================================================|
| Achievements | Collections | Statistics                        |
|----------------------------------------------------------------|
|                                                                |
| Completion Dashboard                                           |
|                                                                |
| Recent Unlocks                                                 |
| Missing Collectibles                                           |
| Progress Charts                                                |
|                                                                |
|----------------------------------------------------------------|
| Status                                  Action Buttons         |
+----------------------------------------------------------------+

# Archive
+----------------------------------------------------------------+
| Archive                                                        |
|================================================================|
| Browser | Incidents | Timeline | Statistics                    |
|----------------------------------------------------------------|
| Archive List       | Archive Viewer                            |
|--------------------|-------------------------------------------|
| ST-000001          | Marker Log                                |
| ST-000002          | Boss Log                                  |
| ST-000003          | Achievements                              |
| ST-000004          | Collectibles                              |
|                    | Incidents                                 |
|                    | Notes                                     |
|----------------------------------------------------------------|
| Status                                  Action Buttons         |
+----------------------------------------------------------------+

# Reference
+----------------------------------------------------------------+
| Reference                                                      |
|================================================================|
| Bosses | Sets | Skills | Buffs | Collectibles | Search         |
|----------------------------------------------------------------|
|                                                                |
| Search Results                                                 |
|                                                                |
| Details                                                        |
|                                                                |
| Linked Information                                             |
|                                                                |
|----------------------------------------------------------------|
| Status                                  Action Buttons         |
+----------------------------------------------------------------+

# Settings
+----------------------------------------------------------------+
| Settings                                                       |
|================================================================|
| General | Appearance | Data | Backup | About                   |
|----------------------------------------------------------------|
|                                                                |
| Settings Panel                                                 |
|                                                                |
|----------------------------------------------------------------|
| Status                                  Save / Cancel          |
+----------------------------------------------------------------+



Broadcast Desk
        │
        ▼
Current Run ◄──── Stream Events
        ▲               │
        │               ▼
Achievement Run     Incident Report
        │               │
        └──────► Archive

        
# Comp Builder Flow Engine

Character
        │
        ▼
Build
(gear, skills, CP, race, class)
        │
        ▼
Capability Resolver
"What buffs, debuffs, synergies, and stats does this build produce?"
        │
        ▼
Composition Analyzer
"What does the raid have, what's missing, what's duplicated?"
        │
        ▼
Recommendation Engine
"What's the smallest change that improves the group?"        

# Capability Tags
I'd introduce a concept called Capability Tags.
Instead of every piece of gear hardcoding logic, everything produces standardized tags.
ex:
Major Slayer
Category: Buff
Source: Gear
Provider: Roaring Opportunist
Duration: 12
Cooldown: 20
Coverage: Variable
Stackable: No