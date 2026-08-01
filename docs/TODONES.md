# Done
- [x] Complete incidenet form checklist status
- [x] Complete incidenet form checklist responisble party
- [x] Complete incidenet form checklist severity
- [x] Complete incidenet form fields
- [x] Complete incidenet form wiring to to the Foundry App
- [x] Complete incidenet form wiring to the OBS Lua
- [x] Create Archive md form for all forms to write to from App (IR done; FN still on old path, EX/AR not built yet)
- [x] Create file number system based on type of form (IR, FN, EX, AR) (ArchiveService supports all 4; FN/EX/AR not yet wired to use it)
- [x] add pulldown with otter variables
- [x] coffee level number randomizer
- [x] wire FN_Expedition and FN_Location to correct json - they can mirror Expedition and Objective values respectively
- [x] icon for app in taskbar
- [x] fix the desktop launch button/make a launchable? I just want to be able to open withtout the terminal (use Launch Foundry.vbs for the desktop shortcut now)
- [x] add labels to app on Field Office tab, the left half should denote that its for the Top bar, and the right half needs to be reorganized a little. 
- [x] I would love a stream title and live notification generator in my brand voice (Broadcast Desk now returns 5-10 titles + 5-8 notifications, click to copy; notifications capped at 140 chars)
- [x] 🌿 Natural history narrator - one hotkey that pops up funny notes on the screen - see Natural_history_narrator.md (data/natural_history_narrator.json now populated from your real .md file; NAR Note group auto-shows and hides itself 30s later)
- [x] So We add a General Observations, Wipes, Pull Starts, Boss Clears, Healers, Tanks, DPS, ☕ BRB, 🤣 Funny Moments, 📖 Progression, 🌙 End of Stream buttons to the App. And when i push those stuff happens. (New Stream Events tab - set BRB/End of Stream scene names in Settings to match your real OBS scene names, and customize data/natural_history_narrator.json with your real lines - currently placeholders)
    - [x] BRB - switches to my BRB page, marks the chapter with BRB
    - [x] Pull Starts - incriments up the pull counter for that stream, and if I've chosen which achievement I'm going for, how many puls on that boss? the very first pull on a boss, marks a chapter - I can denote that manually
    - [x] Boss clears marks a chapter in the stream, names it for the boss we cleared, posts a Nature History Narrator funny thing
    - [x] Wipes - incriments up the number of wipes on that boss, and has a box for me to add the percentage we were able to get to and records that. Posts something from the Natural History Narrator - maybe I can check a box and it will post something so if we're having a tough night its not annoying. 
    - [x] 🌙 End of Stream buttons - changes my stream page to ending
    - [x] General Observations - posts something Natural history narrator
    - [x] Healers - posts something Natural history narrator
    - [x] Tanks - posts something Natural history narrator
    - [x] DPS - posts something Natural history narrator
    - [x] 🤣 Funny Moments - posts something Natural history narrator
    - [x] 📖 Progression - posts something Natural history narrator
    - [x] Clipboard section: Move the first 4 check mark variables above observation. 
    - [x] Fieldnote section: observation, context, next steps, and last three check marks (in progress, complete, under review)
- [x] fix narrator note - wrong function name (obs_frontend_source_list_free -> source_list_release) meant the visibility toggle crashed every time; fixed. This was also the same root cause as the BRB/Ending error below.
OBS_Foundry_v1.4.lua] Failed to call timer_cb for timer_call: [string "C:/Users/nourg/OneDrive/Desktop/Black Feather..."]:572: attempt to call field 'obs_frontend_source_list_free' (a nil value)
- [x] That dungeon/trial pulldown menu on the achievement tab is missing a lot (rebuilt from the real parsed game data: all Trials, base Dungeons, DLC Dungeons, plus Arenas as a bonus - still editable if something very new is missing)
    Trials: Hel Ra Citadel, Aetherian Archive, Sanctum Ophidia,Maw of Lorkhaj,Halls of Fabrication,Asylum Sanctorium,Cloudrest,Sunspire,Kyne's Aegis,Rockgrove,Dreadsail Reef,Sanity's Edge,Lucent Citadel
    Dungeons: Arx Corinium, Ashen Scar, Bal Sunnar, Bedlam Veil, Black Drake Villa, Black Gem Foundry, Blackheart Haven, Blessed Crucible, Bloodroot Forge, Castle Thorn, City of Ash I, City of Ash II, Coral Aerie, Cradle of Shadows, Crypt of Hearts I, Crypt of Hearts II, Darkshade Caverns I, Darkshade Caverns II, Depths of Malatar, Earthen Root Enclave, Elden Hollow I, Elden Hollow II, Exiled Redoubt, Falkreath Hold, Fang Lair, Frostvault, Fungal Grotto I, Fungal Grotto II, Graven Deep, Imperial City Prison, Icereach, Lair of Maarselok, Lep Seclusa, March of Sacrifices, Moon Hunter Keep, Moongrave Fane, Naj Caldeesh, Oathsworn Pit, Red Petal Bastion, Ruins of Mazzatun, Scalecaller Peak, Scrivener's Hall, Selene's Web, Shipwright's Regret, Spindleclutch I, Spindleclutch II, Stone Garden, Stonethorn, Tempest Island, The Banished Cells I, The Banished Cells II, The Cauldron, The Dread Cellar, Unhallowed Grave, Vaults of Madness, Volenfell, White-Gold Tower.
- [x] please look at Brand Voice.md and then take another crack at the title and live stream notification generator (rewrote both generators against the real doc - calm/observational/dry, avoiding all the "words we avoid" list, using the vocabulary list directly)
- [x] I removed the Streamup Chapter Marker Plugin - is that going to break anything? (No - chapter marking uses OBS's own built-in obs_frontend_recording_add_chapter, never depended on StreamUp)
- [x] I get the same error when I use the BRB and Ending button too (same root cause as the narrator note bug - fixed)
- [x] add some way that makes it more obvious that I've pushed the 'wipe' button (flashes gold + status bar shows the running wipe count)
- [x] button for "ult pull" it can be in-line with the 'pull starts button' but smaller and not incriment the total pulls, boss pulls, or wipes on boss
- [x] incident report departments? what are they? (just free text, no fixed list - happy to turn it into a dropdown matching your Trials/Dungeons/Functional OBS folders if that'd help)
- [x] I am not getting an file with the timestamps from Stream Events... (root cause: regular Pull Starts/Wipes never wrote to MarkerLog.md at all - only events that also created a chapter marker did. Added a LogLabel channel so every pull and wipe logs now, with boss name, pull number, wipe number, and % reached - all timestamped by stream-elapsed time first, wall clock second)
- [x] change the name of Odds & Ends to Collections
- [x] Parsed full ESO achievement/collectible/recipe data from the PHP exports into structured JSON
- [x] Analyzed the real BFF spreadsheet (BFF_Achievements_.xlsx) - confirmed R/J checkmark columns, achievement tab layout (A=R, B=J, C=name, F=points, G=description), and that trial achievements are nested inside DLC chapter tabs, not their own tab
- [x] Built GoogleSheetsService - indexes achievements by name across all ~50 achievement tabs (sidesteps the category-to-tab mapping 
- [x] I think I want 3 buttons on the bottom of the main app section. Clear (to clear the contents of that tab), Save to OBS (to send contents of that tab to OBS), and Save to Archive (to save contents of tab to md file and all the places we are archiving data). (Done on Broadcast Desk, Field Office, Incident Report, Achievement Run - reused existing save/archive logic where it fit, built new OBS-output for Broadcast Desk and Achievement Run since they had none before. Skipped Stream Events per your call - it does not fit the single-form model, its buttons already push to OBS individually.)


## Field Office
- [x] can you add '/ Conditions' to the Field Office Context box greyed out prompt area in side the text box
- [x] and change 'Next Steps' to 'Recommendations for Future Adventurers' 


## Stream Events
- [x] When I press Reset Pull/Wipe counters button on Stream events, also clear current boss box
- [x] Archive tab that shows what is being saved when I push the buttons on Stream Events (new Archive Log tab, shows MarkerLog.md and BossLog.md with a Refresh button; also fixed a bug where clicking Save Settings would have silently reset several newer settings like the Google Sheets config back to defaults)
-

## Achievement Run Tracker
- [x] What is the Run ID AR- for? Can we make that useable? (It already is - AR-#### is assigned the moment you archive a run, same numbering system as Incident Reports/Field Notes. It shows as a placeholder AR-— until then, which is why it looked inert.)


## Broadcast Desk

- [X] I changed my mind lol please replace the tone pulldown words with: Focused (Field Notes), Funny (Mostly According to Plan), Questing (Into the Wilds), Hardmode  (Ready Check)   
 [x] on the Broadcast desk can you please add a box for me to include the team name or members names please. Team name is part of my brand stream name thingy. lol So it can go into the generation. The team name can go at the end of the stream name. (STREAM TYPES glyph system + TITLE FORMULAS not yet built - want to talk through how that should relate to the existing Expedition Type dropdown before I build it)
        STREAM TYPES:
        ◇ Achievement Push
        ⬢ Core / Hardmode / Challenge
        △ Calibration / Learning
        ▸ Progression / PvP / Campaign
        ○ Chill / Community

        ========================================
        TITLE FORMULAS
        ========================================
        PvE:
        [GLYPH] TRIAL/DUNGEON | OBJECTIVE | TEAM
        [GLYPH] CONTENT | OBJECTIVE | TEAM
        [GLYPH] TYPE | TEAM | GOAL

        PvP:
        [GLYPH] CAMPAIGN | FIELD OPERATIONS
        [GLYPH] CYRODIIL | OBJECTIVE
        [GLYPH] IMPERIAL CITY | OBJECTIVE


- [x] Parsed full ESO achievement/collectible/recipe data from the PHP exports into structured JSON
- [x] Analyzed the real BFF spreadsheet (BFF_Achievements_.xlsx) - confirmed R/J checkmark columns, achievement tab layout (A=R, B=J, C=name, F=points, G=description), and that trial achievements are nested inside DLC chapter tabs, not their own tab
- [x] Built GoogleSheetsService - indexes achievements by name across all ~50 achievement tabs (sidesteps the category-to-tab mapping 


- [x] the Settings tab now shows the Achievement Run info. The Achievement Run tab now shows the Incident Report now shows Mark Logs and Boss Pull Logs. I cannot see the Settings tab info at all.


- [x] Break Odds & Ends out into its own submenu with headings for the achievements (master-detail layout: category list on the left acts as the submenu, click one to see its subcategories/achievements on the right, instead of one big nested tree)
- [x] a way to clear the marker log and boss log boxes just so the data doesnt show - I dont want to remove the data (clear_archive() only clears the display, never touches MarkerLog.md/BossLog.md - confirmed correct)
- [x] Save to Archive / Clear buttons built and working (archive_current_run/get_next_archive_number/clear_archive) - fixed on merge: was using a bare relative "archives" folder (unpredictable location depending on how the app gets launched) instead of a proper Settings-driven path, had duplicated code, a stray debug print(), and archived whatever was in the on-screen view instead of refreshing from disk first (risk of archiving stale data). All fixed - now uses SessionArchiveFolder setting (default ../Archive/Sessions) and refreshes before archiving.

- [x] Automatic Earth Date metadata
- [x] Automatic Earth Time metadata
- [x] Timezone recording
- [X] move refresh button to the bottom

## UI
- [ ] UI font colors
        COLORS = {
    "paper": "#F5ECD8",
    "paper_dark": "#E7D9BC",
    "border": "#B68A3A",
    "sidebar": "#2C2017",
    "accent": "#8A5A18",
    "success": "#315A38"
}

- [ ] UI Fonts
    # ==========================================
    # fonts.py
    # ==========================================

    class Fonts:
    TITLE = ("Cinzel", 34, "bold")
    SUBTITLE = ("Cormorant Garamond", 14, "italic")

    SECTION = ("Cinzel", 15, "bold")

    LABEL = ("Source Serif 4", 12, "bold")
    INPUT = ("Source Serif 4", 13)
    BODY = ("Source Serif 4", 13)

    TABLE_HEADER = ("Source Serif 4", 12, "bold")
    TABLE = ("Source Serif 4", 12)

    SIDEBAR = ("Cormorant Garamond", 18, "bold")
    LOGO = ("Cinzel", 22, "bold")

    NOTE = ("Cormorant Garamond", 15, "italic")

    STATUS = ("Cormorant Garamond", 12, "italic")
    SMALL = ("Source Serif 4", 10)
    font=Fonts.TITLE
    font=Fonts.SECTION
    font=Fonts.BODY
    font=Fonts.LABEL

- [ ]Use background_paper.png as the base background for every page.
    Requirements:
    - Fill the entire application window.
    - Keep it behind all widgets.
    - Do not tile the image.
    - Frames should use a semi-transparent parchment color so a hint of the paper texture remains visible.
    - Preserve the existing color palette (#F5ECD8, #E7D9BC, #B68A3A).
    - The background should remain fixed while navigating between pages.   

- [ ] Refactor this page using modern desktop UI spacing principles. Create a consistent visual grid with equal margins, equal padding, and aligned controls. Increase whitespace, standardize widget heights, and improve visual hierarchy while preserving all existing functionality and event bindings. The goal is to make the page resemble a premium field journal application rather than a traditional Windows form.

- [ ] Replace the existing reminder panel with the image "remember_note.png".
        Requirements:
        - Display the image at its native aspect ratio.
        - Place it in the lower-left sidebar.
        - Add approximately 16px padding from the sidebar edges.
        - Do not stretch or distort the image.
        - Scale proportionally if the window is resized.
        - The image is decorative only and does not require user interaction.
        - Keep the existing parchment theme and allow the note to visually float on the dark sidebar background.

-[ ] Add the Black Feather Foundry logo to the top-left corner of the application's sidebar.
        Requirements:
        - Load the logo from BFF logo.png.
        - Display it centered at the top of the sidebar.
        - Preserve the image's aspect ratio.
        - Do not stretch or distort the logo.
        - Add approximately 24px of padding above and below the logo.
        - Place the navigation menu directly beneath the logo.
        - Use the existing dark brown sidebar background.
        - The logo should remain fixed while switching pages.
        - Do not modify any existing navigation logic or event handlers.

- [ ] Refactor the application's UI so it no longer uses native QGroupBox widgets.
        Create a reusable SectionCard component based on QFrame.

        Requirements:

        • Decorative title tab overlapping the top border.
        • Rounded parchment card background.
        • Antique brass border.
        • Consistent padding and margins.
        • Accept any existing layouts and widgets without changing functionality.
        • Support nested layouts.
        • Automatically resize with the parent window.
        • Expose methods for changing the title.
        • Centralize all styling in a single QSS stylesheet.

        The objective is to establish a reusable visual design system that every page can share.      

- [ ] Redesign the application's left sidebar into a permanent navigation panel while preserving all existing functionality.
        Requirements:

        • Keep the current navigation buttons and their event handlers.
        • Do not change any application logic.
        • The sidebar should remain fixed while page content changes.

        Visual Layout:

        ------------------------------------------------
        |                                              |
        |                Theme Logo                    |
        |                                              |
        |              Application Name                |
        |                                              |
        |              Theme Subtitle                  |
        |                                              |
        |----------------------------------------------|
        |                                              |
        |  Navigation Buttons                          |
        |                                              |
        |----------------------------------------------|
        |                                              |
        |  Theme Decoration (Sticky Note / Art)        |
        |                                              |
        |----------------------------------------------|
        |                                              |
        |  Version Information                         |
        |                                              |
        ------------------------------------------------

        Styling:

        • Sidebar width approximately 240-260 pixels.
        • Dark theme background.
        • 24px padding around all content.
        • 16px spacing between major sections.
        • Navigation buttons should share identical height and spacing.
        • Active page should be visually highlighted.
        • Add subtle hover effects.
        • Use icons beside each navigation item.
        • Keep the sidebar visually separate from the main content.
        • All spacing should be consistent across every page.

        The sidebar should become the visual identity of the application rather than simply a place to store buttons.        

- [ ] Replace all navigation and action icons with a single consistent SVG icon set.
        Requirements:

        • Use one icon family throughout the application.
        • Icons should be simple, monochrome, and fit the field journal aesthetic.
        • All navigation items should have matching icon sizes (20-24px).
        • Use the application's accent color for active icons.
        • Preserve all existing functionality.
        • Store all icons in a central assets/icons folder.

        Replace the existing button layout with a unified bottom command bar.
- [ ] Modernize all buttons.
        Requirements:

        • Place all primary actions in a single horizontal toolbar.
        • Equal button heights.
        • Equal spacing.
        • Primary action on the far right.
        • Secondary actions to the left.
        • Buttons should share identical styling.
        • Preserve existing click events.
- [ ] Improve all tables.
        Requirements:

        • Increase row height.
        • Alternate subtle row colors.
        • Bold headers.
        • Consistent padding.
        • Rounded table container.
        • Highlight selected rows.
        • Preserve sorting and functionality.
- [ ] Increase spacing within all forms.
        Move labels above controls instead of beside them where practical.

        Align all controls to a consistent grid.

        Standardize field widths.       
- [ ]         

---

## LOW Priority
- [ ] Fill in left and right side of incident form page with ???


# -------------------------------------------------
# BLACK FEATHER FOUNDRY
# FIELD OFFICE UI PALETTE
# -------------------------------------------------

COLORS = {

    # Main Window
    "bg": "#E8DDCB",

    # Frames / Panels
    "panel": "#F5ECDD",

    # Text Entry Boxes
    "entry_bg": "#FFF9F1",

    # Borders / Separators
    "border": "#8A7358",

    # Primary Text
    "text": "#2E261E",

    # Secondary Text
    "subtext": "#6B5A47",

    # Headers
    "header": "#433424",

    # Accent Gold
    "accent": "#B88A45",

    # Success
    "success": "#5D7B5A",

    # Warning
    "warning": "#B97838",

    # Error
    "danger": "#8E4A3B",

    # Buttons
    "button": "#75624D",
    "button_hover": "#8A7358",
    "button_pressed": "#5B4B3B",

    # Button Text
    "button_text": "#F8F4EC",

    # Input Focus
    "focus": "#C69A4A",

    # Disabled
    "disabled": "#C7BCA9"
}


style.configure(".", background="#E8DDCB")

style.configure(
    "TFrame",
    background="#F5ECDD"
)

style.configure(
    "TLabel",
    background="#F5ECDD",
    foreground="#2E261E"
)

style.configure(
    "Header.TLabel",
    font=("Cinzel", 14, "bold"),
    foreground="#433424",
    background="#F5ECDD"
)

style.configure(
    "TButton",
    background="#75624D",
    foreground="#F8F4EC"
)

style.map(
    "TButton",
    background=[
        ("active", "#8A7358"),
        ("pressed", "#5B4B3B")
    ]
)

Window          #E8DDCB

Panels          #F5ECDD

Entries         #FFF9F1

