-- OBS Lua/OBS_Foundry_v1.5.lua
obs=obslua

local JSON_FILE = [[C:\Dev\BFF\FoundryDock\data\CurrentExpedition.json]]
local BROADCAST_FILE = [[C:\Dev\BFF\FoundryDock\data\CurrentBroadcast.json]]
local JSON_INCIDENT_FILE = [[C:\Dev\BFF\FoundryDock\data\CurrentIncident.json]]
local COUNTER_FILE = [[C:\Dev\BFF\FoundryDock\data\FieldNoteCounter.txt]]
local WEATHER_FOLDER=[[C:\Dev\BFF\FoundryDock\data\Weather\]]
local MARKER_LOG_FILE = [[C:\Dev\BFF\FoundryDock\data\MarkerLog.md]]
local STREAM_EVENTS_FILE = [[C:\Dev\BFF\FoundryDock\data\StreamEvents.json]]



----------------------------------------------------------
-- Chapter Marker Tracking
----------------------------------------------------------

local auto_chapters_enabled = true

local marker_state = {
    field_note_number = nil,
    field_note_initialized = false,
    incident_report_number = nil,
    incident_initialized = false,
}

-- Tracks elapsed time ourselves, since the frontend API doesn't expose
-- "current position" directly to scripts. Streaming has no pause concept in
-- OBS, so only recording needs pause tracking.
local stream_started_at = nil

local recording_started_at = nil
local recording_paused_at = nil
local recording_paused_total = 0

local function get_stream_elapsed_seconds()
    if not stream_started_at then return nil end
    return os.time() - stream_started_at
end

local function get_recording_elapsed_seconds()
    if not recording_started_at then return nil end
    local paused = recording_paused_total
    if recording_paused_at then
        paused = paused + (os.time() - recording_paused_at)
    end
    return os.time() - recording_started_at - paused
end

local function format_elapsed(seconds, inactive_label)
    if not seconds then return inactive_label end
    local h = math.floor(seconds / 3600)
    local m = math.floor((seconds % 3600) / 60)
    local s = seconds % 60
    return string.format("%02d:%02d:%02d", h, m, s)
end

local function log_marker(label)
    local stream_elapsed = format_elapsed(get_stream_elapsed_seconds(), "not streaming")
    local recording_elapsed = format_elapsed(get_recording_elapsed_seconds(), "not recording")
    local line = string.format(
        "%s | %s | Stream: %s | Recording: %s\n",
        os.date("%Y-%m-%d %H:%M:%S"),
        label,
        stream_elapsed,
        recording_elapsed
    )
    local f = io.open(MARKER_LOG_FILE, "a")
    if f then
        f:write(line)
        f:close()
    end
end

local function on_recording_frontend_event(event)
    if event == obs.OBS_FRONTEND_EVENT_STREAMING_STARTED then
        stream_started_at = os.time()
    elseif event == obs.OBS_FRONTEND_EVENT_STREAMING_STOPPED then
        stream_started_at = nil
    elseif event == obs.OBS_FRONTEND_EVENT_RECORDING_STARTED then
        recording_started_at = os.time()
        recording_paused_at = nil
        recording_paused_total = 0
    elseif event == obs.OBS_FRONTEND_EVENT_RECORDING_STOPPED then
        recording_started_at = nil
        recording_paused_at = nil
        recording_paused_total = 0
    elseif event == obs.OBS_FRONTEND_EVENT_RECORDING_PAUSED then
        recording_paused_at = os.time()
    elseif event == obs.OBS_FRONTEND_EVENT_RECORDING_UNPAUSED then
        if recording_paused_at then
            recording_paused_total = recording_paused_total + (os.time() - recording_paused_at)
            recording_paused_at = nil
        end
    end
end

----------------------------------------------------------
-- Field Office State
----------------------------------------------------------

local office = {
    expedition = "",
    location = "",
    difficulty = "",
    objective = "",
    weather = "Clear",
    coffee = "",
    coffeeLevel = "",
    engineering = "",
    incidents = "",
    team = "",
    title = "",
    assignment = "",
    statusObserve = false,
    statusDocument = false,
    statusLearn = false,
    statusShareTheLesson = false,
    statusInProgress = false,
    statusComplete = false,
    statusUnderReview = false,
    context = "",
    notesForExplorers = "",
    randomNotes = "",
}

local function json_escape(value)
    local s = tostring(value or "")
    s = string.gsub(s, "\\", "\\\\")
    s = string.gsub(s, '"', '\\"')
    s = string.gsub(s, "\r", "\\r")
    s = string.gsub(s, "\n", "\\n")
    s = string.gsub(s, "\t", "\\t")
    return s
end

local function read_existing_value(path, key)
    local f = io.open(path, "r")
    if not f then return "" end
    local contents = f:read("*all") or ""
    f:close()
    return string.match(contents, '"' .. key .. '"%s*:%s*"([^"]*)"') or ""
end

local function status_json()
    return string.format(
        '{"Observe":%s,"Document":%s,"Learn":%s,"ShareTheLesson":%s,"InProgress":%s,"Complete":%s,"UnderReview":%s}',
        tostring(office.statusObserve),
        tostring(office.statusDocument),
        tostring(office.statusLearn),
        tostring(office.statusShareTheLesson),
        tostring(office.statusInProgress),
        tostring(office.statusComplete),
        tostring(office.statusUnderReview)
    )
end

----------------------------------------------------------
-- Write Current Expedition
----------------------------------------------------------

local function write_json_string(file, key, value, comma)
    local suffix = comma and "," or ""
    file:write(string.format('    "%s":"%s"%s\n', key, json_escape(value), suffix))
end

local function save_json()
    local expedition_file = io.open(JSON_FILE, "w")
    if not expedition_file then
        print("Foundry Dashboard: couldn't open CurrentExpedition.json")
        return
    end

    local status = status_json()

    expedition_file:write("{\n")
    write_json_string(expedition_file, "Expedition", office.expedition, true)
    write_json_string(expedition_file, "Location", office.location, true)
    write_json_string(expedition_file, "Difficulty", office.difficulty, true)
    write_json_string(expedition_file, "Objective", office.objective, true)
    write_json_string(expedition_file, "Goal", office.objective, true)
    write_json_string(expedition_file, "Weather", office.weather, true)
    write_json_string(expedition_file, "Coffee", office.coffee, true)
    write_json_string(expedition_file, "CoffeeLevel", office.coffeeLevel, true)
    write_json_string(expedition_file, "Engineering", office.engineering, true)
    write_json_string(expedition_file, "Incidents", office.incidents, true)
    write_json_string(expedition_file, "Team", office.team, true)
    write_json_string(expedition_file, "Title", office.title, true)
    write_json_string(expedition_file, "Assignment", office.assignment, true)
    write_json_string(expedition_file, "Context", office.context, true)
    write_json_string(expedition_file, "NextSteps", office.notesForExplorers, true)
    write_json_string(expedition_file, "NotesForExplorers", office.notesForExplorers, true)
    write_json_string(expedition_file, "Content", office.randomNotes, true)
    write_json_string(expedition_file, "RandomNotes", office.randomNotes, true)
    expedition_file:write(string.format('    "Status":%s\n', status))
    expedition_file:write("}\n")
    expedition_file:close()

    local notification = read_existing_value(BROADCAST_FILE, "Notification")
    local broadcast_file = io.open(BROADCAST_FILE, "w")
    if not broadcast_file then
        print("Foundry Dashboard: couldn't open CurrentBroadcast.json")
        return
    end

    broadcast_file:write("{\n")
    write_json_string(broadcast_file, "Title", office.title, true)
    write_json_string(broadcast_file, "Team", office.team, true)
    write_json_string(broadcast_file, "Notification", notification, true)
    write_json_string(broadcast_file, "Expedition", office.expedition, true)
    write_json_string(broadcast_file, "Location", office.location, true)
    write_json_string(broadcast_file, "Difficulty", office.difficulty, true)
    write_json_string(broadcast_file, "Objective", office.objective, true)
    write_json_string(broadcast_file, "Weather", office.weather, true)
    write_json_string(broadcast_file, "Coffee", office.coffee, true)
    write_json_string(broadcast_file, "CoffeeLevel", office.coffeeLevel, true)
    write_json_string(broadcast_file, "Engineering", office.engineering, true)
    write_json_string(broadcast_file, "Incidents", office.incidents, true)
    write_json_string(broadcast_file, "Assignment", office.assignment, true)
    write_json_string(broadcast_file, "Context", office.context, true)
    write_json_string(broadcast_file, "NextSteps", office.notesForExplorers, true)
    write_json_string(broadcast_file, "Observation", office.randomNotes, true)
    broadcast_file:write(string.format('    "Status":%s\n', status))
    broadcast_file:write("}\n")
    broadcast_file:close()

    print("Foundry Dashboard: overlay data saved.")
end
--------------------------------------------------
-- Weather Engine
--------------------------------------------------
local WEATHER_FILES={
["Clear"]="clear.png",
["Partly Cloudy"]="partly_cloudy.png",
["Cloudy"]="cloudy.png",
["Light Rain"]="rain_light.png",
["Heavy Rain"]="rain_heavy.png",
["Storm"]="storm.png",
["Fog"]="fog.png",
["Snow"]="snow.png",
["Windy"]="wind.png"
}

local function read_file(path)
 local f=io.open(path,"r")
 if not f then return nil end
 local t=f:read("*all")
 f:close()
 return t
end

local function extract(key,text)
 if not text then return "" end
 return string.match(text,'"'..key..'"%s*:%s*"([^"]*)"') or ""
end

local function extract_num(key, text)
    if not text then return nil end
    local val = string.match(text, '"'..key..'"%s*:%s*(-?%d+)')
    if val then return tonumber(val) end
    return nil
end

local function switch_scene(name)
    -- DISABLED: calling obs_frontend_set_current_scene() from a script timer
    -- callback is a confirmed, long-standing OBS crash/freeze bug (OBS GitHub
    -- issues #3385, #6151, #7516). Scene switching now goes through
    -- ObsWebSocketService on the Python side (SetCurrentProgramScene over
    -- OBS's WebSocket server), which doesn't have this problem. This
    -- function is kept only so nothing breaks if StreamEvents.json ever
    -- has a SceneName again; it deliberately no-ops instead of switching.
    if name and name ~= "" then
        print("Foundry: scene switch to '" .. name .. "' requested via Lua but is disabled - use OBS WebSocket instead")
    end
end

local function set_text(name,val)
 local s=obs.obs_get_source_by_name(name)
 if not s then return end
 local d=obs.obs_data_create()
 obs.obs_data_set_string(d,"text",tostring(val))
 obs.obs_source_update(s,d)
 obs.obs_data_release(d)
 obs.obs_source_release(s)
end

local function set_image(name,file)
 local s=obs.obs_get_source_by_name(name)
 if not s then return end
 local d=obs.obs_source_get_settings(s)
 obs.obs_data_set_string(d,"file",file)
 obs.obs_source_update(s,d)
 obs.obs_data_release(d)
 obs.obs_source_release(s)
end

local function format_coffee_level(value)
    local text = tostring(value or "")
    if text == "" then return "" end
    if string.sub(text, -1) == "%" then return text end
    return text .. "%"
end

local function update_weather_icon(weather_name)
    local filename = WEATHER_FILES[weather_name]
    if filename then
        set_image("TOP_Weather_Icon", WEATHER_FOLDER .. filename)
    end
end

----------------------------------------------------------
-- Tamriel Calendar
----------------------------------------------------------

local TAMRIEL_MONTHS = {
    "Morning Star",
    "Sun's Dawn",
    "First Seed",
    "Rain's Hand",
    "Second Seed",
    "Mid Year",
    "Sun's Height",
    "Last Seed",
    "Hearthfire",
    "Frostfall",
    "Sun's Dusk",
    "Evening Star"
}

local TAMRIEL_WEEKDAYS = {
    "Morndas",
    "Tirdas",
    "Middas",
    "Turdas",
    "Fredas",
    "Loredas",
    "Sundas"
}

----------------------------------------------------------
-- Field Note Counter
----------------------------------------------------------

local function get_field_note_number()

    local file = io.open(COUNTER_FILE, "r")

    if file == nil then
        return 1
    end

    local number = tonumber(file:read("*all")) or 1

    file:close()

    return number

end

local function save_field_note_number(number)

    local file = io.open(COUNTER_FILE, "w")

    if file then
        file:write(tostring(number))
        file:close()
    end

end

local function next_field_note()

    local number = get_field_note_number()

    number = number + 1

    save_field_note_number(number)

    return number

end

----------------------------------------------------------
-- Checkbox Image
----------------------------------------------------------

local CHECK_FOLDER = [[C:\Dev\BFF\FoundryDock\data\]]
function set_checkbox(source_name, checked)

    local filename

    if checked then
        filename = "check.png"
    else
        filename = "blank.png"
    end

    local source = obs.obs_get_source_by_name(source_name)

    if source ~= nil then

        local settings = obs.obs_source_get_settings(source)

        obs.obs_data_set_string(
            settings,
            "file",
            CHECK_FOLDER .. filename
        )

        obs.obs_source_update(source, settings)

        obs.obs_data_release(settings)
        obs.obs_source_release(source)

    end

end

----------------------------------------------------------
-- Tamriel Date
----------------------------------------------------------

local function get_tamriel_date()

    ------------------------------------------------------
    -- Anchor Date
    ------------------------------------------------------

    local anchorEarth = os.time({
        year = 2026,
        month = 7,
        day = 23,
        hour = 12
    })

    local anchorDay = 23
    local anchorMonth = 7      -- Sun's Height
    local anchorYear = 582

    ------------------------------------------------------

    local today = os.time()

    local days = math.floor((today - anchorEarth) / 86400)

    local day = anchorDay + days
    local month = anchorMonth
    local year = anchorYear

    while day > 30 do
        day = day - 30
        month = month + 1

        if month > 12 then
            month = 1
            year = year + 1
        end
    end

    while day < 1 do
        month = month - 1

        if month < 1 then
            month = 12
            year = year - 1
        end

        day = day + 30
    end

    local weekday = TAMRIEL_WEEKDAYS[((days % 7) + 7) % 7 + 1]

    local suffix = "th"

    if day % 10 == 1 and day ~= 11 then
        suffix = "st"
    elseif day % 10 == 2 and day ~= 12 then
        suffix = "nd"
    elseif day % 10 == 3 and day ~= 13 then
        suffix = "rd"
    end

  return string.format(
    "%s, %d%s of %s\n2E %d",
    weekday,
    day,
    suffix,
    TAMRIEL_MONTHS[month],
    year
)

end


function script_defaults(settings)
    obs.obs_data_set_default_string(settings, "weather", "Clear")
    obs.obs_data_set_default_string(settings, "coffee", "Unavailable")
    obs.obs_data_set_default_string(settings, "engineering", "Nominal")
    obs.obs_data_set_default_bool(settings, "status_observe", false)
    obs.obs_data_set_default_bool(settings, "status_document", false)
    obs.obs_data_set_default_bool(settings, "status_learn", false)
    obs.obs_data_set_default_bool(settings, "status_share_the_lesson", false)
    obs.obs_data_set_default_bool(settings, "status_in_progress", false)
    obs.obs_data_set_default_bool(settings, "status_complete", false)
    obs.obs_data_set_default_bool(settings, "status_under_review", false)
    obs.obs_data_set_default_bool(settings, "auto_chapters", true)
end

function script_update(settings)
    office.expedition = obs.obs_data_get_string(settings, "expedition")
    office.location = obs.obs_data_get_string(settings, "location")
    office.difficulty = obs.obs_data_get_string(settings, "difficulty")
    office.objective = obs.obs_data_get_string(settings, "objective")
    office.weather = obs.obs_data_get_string(settings, "weather")
    office.coffee = obs.obs_data_get_string(settings, "coffee")
    office.coffeeLevel = obs.obs_data_get_string(settings, "coffee_level")
    office.engineering = obs.obs_data_get_string(settings, "engineering")
    office.incidents = obs.obs_data_get_string(settings, "incidents")
    office.team = obs.obs_data_get_string(settings, "team")
    office.title = obs.obs_data_get_string(settings, "title")
    office.assignment = obs.obs_data_get_string(settings, "assignment")
    office.statusObserve = obs.obs_data_get_bool(settings, "status_observe")
    office.statusDocument = obs.obs_data_get_bool(settings, "status_document")
    office.statusLearn = obs.obs_data_get_bool(settings, "status_learn")
    office.statusShareTheLesson = obs.obs_data_get_bool(settings, "status_share_the_lesson")
    office.statusInProgress = obs.obs_data_get_bool(settings, "status_in_progress")
    office.statusComplete = obs.obs_data_get_bool(settings, "status_complete")
    office.statusUnderReview = obs.obs_data_get_bool(settings, "status_under_review")
    office.context = obs.obs_data_get_string(settings, "context")
    office.notesForExplorers = obs.obs_data_get_string(settings, "notes_for_explorers")
    office.randomNotes = obs.obs_data_get_string(settings, "random_notes")

    auto_chapters_enabled = obs.obs_data_get_bool(settings, "auto_chapters")
end


local function update()
    local json = read_file(JSON_FILE)
    if not json then return end

    local fields = {
        Difficulty = "TOP_Difficulty",
        Objective = "TOP_Objective",
        Weather = "TOP_Weather",
        Coffee = "TOP_Coffee",
        CoffeeLevel = "TOP_CoffeeLevel",
        Engineering = "TOP_Engineering",
        Incidents = "TOP_Incidents",
        Date = "CLIP_Date",
        Assignment = "CLIP_Assignment",
        FieldNoteNumber = "FN_Note_Number",
        Observation = "NOTE_Observation",
        Context = "NOTE_Context",
        NextSteps = "NOTE_NextSteps"
    }

    for key, source in pairs(fields) do
        if key == "Date" then
            set_text(source, get_tamriel_date())
        elseif key == "FieldNoteNumber" then
            set_text(source, tostring(get_field_note_number()))
        elseif key == "CoffeeLevel" then
            set_text(source, format_coffee_level(extract(key, json)))
        else
            set_text(source, extract(key, json))
        end
    end

    -- Field Note section mirrors the Top Bar's Expedition/Objective values
    set_text("FN_Expedition", extract("Objective", json))
    set_text("FN_Location", extract("Expedition", json))
    set_text("FN_Observation", extract("Observation", json))
    set_text("NOTE_Content", extract("Content", json))
    set_text("NOTE_Context", extract("Context", json))
     set_text("NOTE_NextSteps", extract("NextSteps", json))
    -- set_text("FN_Difficulty", extract("Difficulty", json))

    local w = extract("Weather", json)
    update_weather_icon(w)

    local status = json:match('"Status"%s*:%s*{(.-)}')
    if status then
        set_checkbox("CHK_Status_Observe", status:match('"Observe"%s*:%s*true') ~= nil)
        set_checkbox("CHK_Status_Document", status:match('"Document"%s*:%s*true') ~= nil)
        set_checkbox("CHK_Status_Learn", status:match('"Learn"%s*:%s*true') ~= nil)
        set_checkbox("CHK_Status_Share_the_Lesson", status:match('"ShareTheLesson"%s*:%s*true') ~= nil)
        set_checkbox("CHK_Status_In_Progress", status:match('"InProgress"%s*:%s*true') ~= nil)
        set_checkbox("CHK_Status_Complete", status:match('"Complete"%s*:%s*true') ~= nil)
        set_checkbox("CHK_Status_Under_Review", status:match('"UnderReview"%s*:%s*true') ~= nil)
    end

    local field_note_number = get_field_note_number()
    if marker_state.field_note_initialized then
        if auto_chapters_enabled and field_note_number ~= marker_state.field_note_number then
            obs.obs_frontend_recording_add_chapter("Field Note " .. tostring(field_note_number))
            log_marker("Field Note " .. tostring(field_note_number))
        end
    else
        marker_state.field_note_initialized = true
    end
    marker_state.field_note_number = field_note_number
end

----------------------------------------------------------
-- Incident Report
----------------------------------------------------------

local SEVERITY_CHECKBOXES = {
    Minor = "CHK_Sev_Minor",
    Moderate = "CHK_Sev_Moderate",
    Major = "CHK_Sev_Major",
    Critical = "CHK_Sev_Critical",
}

local function update_incident()
    local json = read_file(JSON_INCIDENT_FILE)
    if not json then return end

    local fields = {
        Location = "IR_Location",
        Department = "IR_Dept",
        Summary = "IR_Suamary",
        SuspectedCause = "IR_Suspected_Cause",
        EngineeringAssessment = "IR_Engineering_Assessment",
        CoffeeRecommendation = "IR_Coffee_Reccomendation",
        Observations = "IR_Observations",
        ActionsTaken = "IR_Actions_Taken",
        Recommendations = "IR_Reccomendations",
        ReportNumber = "IR_Note_Number",
        OutstandingQuestions = "IR_Outstanding_Questions"
    }

    for key, source in pairs(fields) do
        set_text(source, extract(key, json))
    end

    local severity = extract("Severity", json)
    for level, source in pairs(SEVERITY_CHECKBOXES) do
        set_checkbox(source, level == severity)
    end

    local party = json:match('"ResponsibleParty"%s*:%s*{(.-)}')
    if party then
        set_checkbox("CHK_Moose_Gremlin", party:match('"MooseGremlin"%s*:%s*true') ~= nil)
        set_checkbox("CHK_Lag", party:match('"Lag"%s*:%s*true') ~= nil)
        set_checkbox("CHK_User_Error", party:match('"UserError"%s*:%s*true') ~= nil)
        set_checkbox("CHK_ESO", party:match('"ESO"%s*:%s*true') ~= nil)
        set_checkbox("CHK_Unknown", party:match('"Unknown"%s*:%s*true') ~= nil)
        set_checkbox("CHK_Under_Investigation", party:match('"UnderInvestigation"%s*:%s*true') ~= nil)
    end

    local status = json:match('"Status"%s*:%s*{(.-)}')
    if status then
        set_checkbox("CHK_Filed", status:match('"Filed"%s*:%s*true') ~= nil)
        set_checkbox("CHK_Pending_Review", status:match('"PendingReview"%s*:%s*true') ~= nil)
        set_checkbox("CHK_Requires_Follow_Up", status:match('"RequiresFollowUp"%s*:%s*true') ~= nil)
        set_checkbox("CHK_Archived", status:match('"Archived"%s*:%s*true') ~= nil)
    end

    local report_number = extract("ReportNumber", json)
    if report_number ~= "" then
        if marker_state.incident_initialized then
            if auto_chapters_enabled and report_number ~= marker_state.incident_report_number then
                obs.obs_frontend_recording_add_chapter("Incident " .. report_number)
                log_marker("Incident " .. report_number)
            end
        else
            marker_state.incident_initialized = true
        end
        marker_state.incident_report_number = report_number
    end
end

----------------------------------------------------------
-- Stream Events (Stream Events tab buttons)
----------------------------------------------------------

local stream_event_state = {
    sequence = nil,
    initialized = false,
}

local NARRATOR_GROUP_NAME = "NAR Note"
local NARRATOR_HIDE_DELAY_MS = 30000

local function set_group_visible(group_name, visible)
    local scenes = obs.obs_frontend_get_scenes()
    if not scenes then return end
    for _, scene_source in ipairs(scenes) do
        local scene = obs.obs_scene_from_source(scene_source)
        if scene then
            local item = obs.obs_scene_find_source(scene, group_name)
            if item then
                obs.obs_sceneitem_set_visible(item, visible)
            end
        end
    end
    obs.source_list_release(scenes)
end

local function hide_narrator_note()
    set_group_visible(NARRATOR_GROUP_NAME, false)
    obs.remove_current_callback()
end

local function show_narrator_note()
    set_group_visible(NARRATOR_GROUP_NAME, true)
    -- Remove any previously pending hide so back-to-back notes each get
    -- their own full 30 seconds rather than being cut short by an older timer.
    obs.timer_remove(hide_narrator_note)
    obs.timer_add(hide_narrator_note, NARRATOR_HIDE_DELAY_MS)
end

local function update_stream_events()
    local json = read_file(STREAM_EVENTS_FILE)
    if not json then return end

    local sequence = extract_num("Sequence", json)
    if sequence == nil then return end

    if not stream_event_state.initialized then
        stream_event_state.initialized = true
        stream_event_state.sequence = sequence
        return
    end

    if sequence == stream_event_state.sequence then
        return
    end
    stream_event_state.sequence = sequence

    local chapter_label = extract("ChapterLabel", json)
    if chapter_label ~= "" then
        if auto_chapters_enabled then
            obs.obs_frontend_recording_add_chapter(chapter_label)
        end
        log_marker(chapter_label)
    else
        local log_label = extract("LogLabel", json)
        if log_label ~= "" then
            log_marker(log_label)
        end
    end

    -- Scene changes are intentionally not performed from this timer callback.
    -- FoundryDock uses OBS WebSocket instead, keeping this timer deadlock-free.

    local narrator_text = extract("NarratorText", json)
    if narrator_text ~= "" then
        set_text("NR_Note", narrator_text)
        show_narrator_note()
    end
end

----------------------------------------------------------
-- Broadcast
----------------------------------------------------------

local function update_broadcast()

    local json = read_file(BROADCAST_FILE)

    if not json then
        print("Foundry: couldn't read BROADCAST_FILE at " .. BROADCAST_FILE)
        return
    end

    ------------------------------------------------------
    -- Broadcast
    ------------------------------------------------------

    set_text(
        "TXT_title",
        extract("Title", json)
    )

    set_text(
        "TXT_team",
        extract("Team", json)
    )

    set_text(
        "TXT_notify",
        extract("Notification", json)
    )

    ------------------------------------------------------
    -- Broadcast Top Bar Fields
    ------------------------------------------------------
    set_text(
        "TOP_Expedition",
        extract("Expedition", json)
    )
     set_text(
        "TOP_Location",
        extract("Location", json)
    )
    
    local broadcast_weather = extract("Weather", json)
    set_text(
        "TOP_Weather",
        broadcast_weather
    )
    update_weather_icon(broadcast_weather)

    set_text(
        "TOP_Objective",
        extract("Objective", json)
    )

    set_text(
        "TOP_Coffee",
        extract("Coffee", json)
    )

    set_text(
        "TOP_CoffeeLevel",
        format_coffee_level(extract("CoffeeLevel", json))
    )

    set_text(
        "TOP_Incidents",
        extract("Incidents", json)
    )

    set_text(
        "TOP_Difficulty",
        extract("Difficulty", json)
    )

    set_text(
        "TOP_Engineering",
        extract("Engineering", json)
    )

    set_text(
        "FN_Observation",
        extract("Observation", json)
    )

    set_text(
        "FN_context",
        extract("Context", json)
    )

    set_text(
        "FN_NextSteps",
        extract("NextSteps", json)
    )
end


----------------------------------------------------------
-- Update All
----------------------------------------------------------

local function update_all()

    update()
    update_incident()
    update_stream_events()
    update_broadcast()

end

function script_properties()
    local props = obs.obs_properties_create()

    obs.obs_properties_add_text(
        props, "dashboard_heading",
        "FOUNDRY Stream Overlay Dashboard",
        obs.OBS_TEXT_INFO
    )

    obs.obs_properties_add_text(props, "expedition", "Expedition", obs.OBS_TEXT_DEFAULT)
    obs.obs_properties_add_text(props, "location", "Location", obs.OBS_TEXT_DEFAULT)
    obs.obs_properties_add_text(props, "objective", "Objective", obs.OBS_TEXT_DEFAULT)
    obs.obs_properties_add_text(props, "difficulty", "Difficulty", obs.OBS_TEXT_DEFAULT)

    local weather = obs.obs_properties_add_list(
        props,
        "weather",
        "Weather",
        obs.OBS_COMBO_TYPE_LIST,
        obs.OBS_COMBO_FORMAT_STRING
    )
    obs.obs_property_list_add_string(weather, "Clear", "Clear")
    obs.obs_property_list_add_string(weather, "Partly Cloudy", "Partly Cloudy")
    obs.obs_property_list_add_string(weather, "Cloudy", "Cloudy")
    obs.obs_property_list_add_string(weather, "Light Rain", "Light Rain")
    obs.obs_property_list_add_string(weather, "Heavy Rain", "Heavy Rain")
    obs.obs_property_list_add_string(weather, "Storm", "Storm")
    obs.obs_property_list_add_string(weather, "Fog", "Fog")
    obs.obs_property_list_add_string(weather, "Snow", "Snow")
    obs.obs_property_list_add_string(weather, "Windy", "Windy")

    local coffee = obs.obs_properties_add_list(
        props,
        "coffee",
        "Coffee",
        obs.OBS_COMBO_TYPE_LIST,
        obs.OBS_COMBO_FORMAT_STRING
    )
    obs.obs_property_list_add_string(coffee, "Unavailable", "Unavailable")
    obs.obs_property_list_add_string(coffee, "Requested", "Requested")
    obs.obs_property_list_add_string(coffee, "Brewing", "Brewing")
    obs.obs_property_list_add_string(coffee, "Operational", "Operational")
    obs.obs_property_list_add_string(coffee, "Enhanced", "Enhanced")
    obs.obs_property_list_add_string(coffee, "Maximum", "Maximum")
    obs.obs_property_list_add_string(coffee, "Experimental", "Experimental")

    obs.obs_properties_add_text(props, "coffee_level", "Coffee Level", obs.OBS_TEXT_DEFAULT)

    local engineering = obs.obs_properties_add_list(
        props,
        "engineering",
        "Engineering",
        obs.OBS_COMBO_TYPE_LIST,
        obs.OBS_COMBO_FORMAT_STRING
    )
    obs.obs_property_list_add_string(engineering, "Nominal", "Nominal")
    obs.obs_property_list_add_string(engineering, "Recursive", "Recursive")
    obs.obs_property_list_add_string(engineering, "Sentient", "Sentient")
    obs.obs_property_list_add_string(engineering, "Unsupervised", "Unsupervised")
    obs.obs_property_list_add_string(engineering, "Orthogonal", "Orthogonal")
    obs.obs_property_list_add_string(engineering, "Ceremonial", "Ceremonial")
    obs.obs_property_list_add_string(engineering, "Migratory", "Migratory")
    obs.obs_property_list_add_string(engineering, "Seasonal", "Seasonal")
    obs.obs_property_list_add_string(engineering, "Temporal", "Temporal")
    obs.obs_property_list_add_string(engineering, "Peripheral", "Peripheral")
    obs.obs_property_list_add_string(engineering, "Ambient", "Ambient")
    obs.obs_property_list_add_string(engineering, "Speculative", "Speculative")
    obs.obs_property_list_add_string(engineering, "Probabilistic", "Probabilistic")
    obs.obs_property_list_add_string(engineering, "Inexplicable", "Inexplicable")
    obs.obs_property_list_add_string(engineering, "Contrarian", "Contrarian")
    obs.obs_property_list_add_string(engineering, "Percolating", "Percolating")
    obs.obs_property_list_add_string(engineering, "Ferrous", "Ferrous")
    obs.obs_property_list_add_string(engineering, "Buoyant", "Buoyant")
    obs.obs_property_list_add_string(engineering, "Obstinate", "Obstinate")
    obs.obs_property_list_add_string(engineering, "Misfiled", "Misfiled")

    obs.obs_properties_add_text(props, "incidents", "Incidents", obs.OBS_TEXT_DEFAULT)
    obs.obs_properties_add_text(props, "team", "Team", obs.OBS_TEXT_DEFAULT)
    obs.obs_properties_add_text(props, "title", "Stream / Expedition Title", obs.OBS_TEXT_DEFAULT)

    obs.obs_properties_add_text(
        props,
        "field_notes_heading",
        "FIELD NOTES / CLIPBOARD",
        obs.OBS_TEXT_INFO
    )

    obs.obs_properties_add_text(
        props, "assignment", "Clipboard Assignment", obs.OBS_TEXT_MULTILINE
    )

    obs.obs_properties_add_text(
        props, "status_heading", "Status", obs.OBS_TEXT_INFO
    )
    obs.obs_properties_add_bool(props, "status_observe", "Observe")
    obs.obs_properties_add_bool(props, "status_document", "Document")
    obs.obs_properties_add_bool(props, "status_learn", "Learn")
    obs.obs_properties_add_bool(props, "status_share_the_lesson", "Share the Lesson")
    obs.obs_properties_add_bool(props, "status_in_progress", "In Progress")
    obs.obs_properties_add_bool(props, "status_complete", "Complete")
    obs.obs_properties_add_bool(props, "status_under_review", "Under Review")

    obs.obs_properties_add_text(props, "context", "Context", obs.OBS_TEXT_MULTILINE)
    obs.obs_properties_add_text(
        props, "notes_for_explorers", "Notes for Future Explorers", obs.OBS_TEXT_MULTILINE
    )
    obs.obs_properties_add_text(
        props, "random_notes", "Random Notes", obs.OBS_TEXT_MULTILINE
    )

    obs.obs_properties_add_button(
        props, "save_dashboard", "Save Dashboard to Overlay", save_pressed
    )
    obs.obs_properties_add_button(
        props, "refresh_incident", "Refresh Incident Report", incident_pressed
    )
    obs.obs_properties_add_bool(
        props, "auto_chapters", "Auto chapter marker on new Field Note / Incident"
    )

    return props
end

function save_pressed(props, property)
    save_json()
    update()
    return true
end

function new_field_note_pressed(props, property)
    print("New Field Note")
    return true
end

function incident_pressed(props, property)
    update_incident()
    print("Incident Report refreshed")
    return true
end

function script_load(settings)

    obs.timer_add(
        update_all,
        1000
    )

    obs.obs_frontend_add_event_callback(
        on_recording_frontend_event
    )

end

function script_unload()

    obs.timer_remove(update_all)

    obs.obs_frontend_remove_event_callback(
        on_recording_frontend_event
    )

end