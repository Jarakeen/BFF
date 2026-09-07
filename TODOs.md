Tasks outside of the master roadmap

- [X] find a nicer desktop icon
- [X] write a nice mundus stone importer
- [X] create a testing installer
- [ ] import Rumors and find a page to put them on
- [ ] create a flow thru of buttons on the broadcast desk to make it more obvious that things are getting sent to OBS and sent to a report for Archive
- [X] add checkboxes - and a way to check off multiple at a time - on the row of Collectibles
- [X] import images for the collectibles and add to each corresponding Collectible (we wrote a tool/parser)
- [X] hook up the google sheets for the achievements page
- [ ] add images to the Achievements?
- [X] redo Settings page to go with the Settings mockup in the Docs folder
- [X] ?? can we rename the ui files safely to better align with what they are or is it just too late for that ??
- [X] create the Boss page from docs (on encounters or mechs?)
- [X] find a standard 'Boss' and 'Double Bosses' icon to use on the boss page
- [X] add a "Pages On/Off" setting on the Settings tab that allows you to hide pages by main menu (Broadcast, Collectible, Acheivement, Raid Engine)
- [ ] Achievement page - details box, make the text much larger - style it like the wireframe
- [X] Create a page for the Collections main menu button with circle and/or line graphs that shows your progress in each submenu category
- [X] | What it actually is                  | Current-ish name           | Better name                                                         |
| ------------------------------------ | -------------------------- | ------------------------------------------------------------------- |
| ESO account achievements             | `collections_page.py`      | `achievements_page.py`                                              |
| ESO collectibles, mounts, pets, etc. | `collectibles_page.py`     | `collectibles_page.py`                                              |
| OBS achievement display/control desk | `achievement_desk_page.py` | `broadcast_achievements_page.py` or                   `achievement_broadcast_page.py` |

-[X] add collectible ownership checkboxes, Shift-range selection, pending changes, and batch save; then rename the confusing Achievements/Collections files and references safely.
-[X] Mechanics doesnt have an icon - can we add one
-[X] we've lost the app icon on the task bar when its running - fix that please
-[X] wherever there are timers in the app - plase make them functional
-[X] whereever there are "edit notes" cards on the app, please make that card a note app and editable
-[X] next to "Provides" card on the Overview page card, please change that to a "thumbs up"
-[X] figure out what to do the the ESO logs page, maybe ask Rik
-[X] make all the timers work
-[X] add an asylum sanctorium timer
-[ ] are there other ESO game timers that would be handy? if so, add them
-[?] wire all the bosses and mechs to the Mechanics page and reference pages
-[X] How do multiple ppl share a roster info?
-[X] make roster output/export 'pretty'
-[X] add the top ESO Logs setups per trial
-[ ] get ms signature file thingy for app completed
-[ ] images for mechs - can they be farmed? uesp?
-[X] Optimaztion - auto fill top buttons to match what they need to be for "generate team"
-[X] figure out how to easily share things like maps and roster to google docs and make it pretty
-[X] fix top logo
-[X] can I document how long bosses are damagable from ESO logs?
-[X] add Help docs
-[ ] timer for bosses - ex add portal timer to Bahse
-[X] beef up Reference data page
-[X] Tools & Timers menu category - add gear/pot/food/skill lookup
-[X] remove the "generated rosters" from assignemnts page 
-[X] remove |cffffff0 from gear lookup
-[X] make scribe simulator actually work
-[ ] make a team merch page
-[X] add stickerbook to Collectibles
-[ ] add an engine that has lots of swaps or only a few swaps for a trial?
-[ ] rylo says it needs to auto update
-[ ] still need more trial info
-[X] art/icons for scribed skills
-[x] why arent the arena weapons in the gear lookup
-[ ] make a MOST page for fun lol ask the app to make a build capabale of the most heals, health, damage, etc (sustain, survivability not required lol)
-[ ] PvP? 
-[X] add an "armor that looks interesting" bookmark tool for comp building
-[ ] can we create builds from screenshots?
-[X] add a dashboard inside OBS so I dont have to run the app if I dont want to
-[ ] Close the encounter-source → canonical encounter-model gap for bosses with rich source data but sparse canonical phase/mechanic rows. Start with Sunspire → Lokkestiiz as the reference implementation. Promote reviewed, source-backed encounter facts such as Aerial Onslaught at 80% / 50% / 20%, boss untargetability during flight, add-active windows, raid-damage windows, and true transition/wait downtime into the canonical encounter model without parsing prose into assumed truth. Preserve provenance and unresolved fields, especially unknown exact add counts or timing. The resulting canonical model must distinguish boss-damageable time, add-damage time, raid-damage/healing-demand time, and genuine inactive transition time so Comp Maker, Optimization, rotation evaluation, and uptime scoring can choose the correct effect-specific denominator. Add an audit that finds other encounters where source data exists but `encounter_phase`, `encounter_mechanic`, `encounter_strategy`, health, or canonical facts are missing, then migrate them through the same reviewed evidence path rather than adding encounter-specific hard-coded exceptions.
  - [ ] Finish the Lokkestiiz reference promotion after the verified dry run: persist only the two accepted reviewed-single-source facts (`damage_window:aerial_onslaught_flight` and `add_group:aerial_onslaught_atronachs`) through the existing schema-v3 writer; verify the write is idempotent on a second run; confirm exactly one preserved evidence row per fact with `reviewed_single_source` provenance; rerun the Sunspire/actionable-gap audit; and add a post-write regression proving no unresolved timing/add-count data was invented and no human review was counted as corroborating source evidence.
